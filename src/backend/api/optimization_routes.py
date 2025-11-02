"""Optimization-related API routes.

This module provides endpoints to manage parameter spaces and optimization jobs.

Key points:
- Create an OptimizationJob in the request handler, then run the blocking optimization
    in a background thread so the HTTP request returns immediately.
- The background worker creates its own DB session (SessionLocal) and updates job
    records as it progresses or fails.
"""

import logging
import asyncio
import math
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models import (
    get_db, Strategy, StrategyParameterSpace, ParameterSet, ParameterSetPerformance, OptimizationJob, OptimizationTrial
)
from ..models.base import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/optimization", tags=["optimization"])


class ParameterSpaceRequest(BaseModel):
    parameter_name: str
    parameter_type: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step_size: Optional[float] = None
    choices: Optional[List[Any]] = None
    description: Optional[str] = None


class OptimizationRequest(BaseModel):
    strategy_id: int
    name: str
    description: Optional[str] = None
    parameter_spaces: List[ParameterSpaceRequest]
    objective_function: str = 'sharpe_ratio'
    n_trials: int = 100
    timeout: Optional[int] = 3600
    backtest_config: Dict[str, Any]

@router.get("/strategies/{strategy_id}/parameter-spec")
async def get_strategy_parameter_spec(
    strategy_id: int,
    db: Session = Depends(get_db)
):
    """
    自动从策略代码中识别参数规范（键、类型、默认值）。

    返回示例：
    {
      "status": "success",
      "data": [
        {"name": "short_window", "type": "integer", "default": 5},
        {"name": "long_window", "type": "integer", "default": 20}
      ]
    }
    """
    try:
        # 读取策略代码
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")

        code = strategy.code
        if isinstance(code, (bytes, bytearray)):
            try:
                code = code.decode('utf-8')
            except Exception:
                code = code.decode('latin-1')

        # 动态加载策略并实例化以获取默认参数
        from .strategy_routes import load_strategy_from_code
        instance = load_strategy_from_code(code, parameters={}, data=None)

        # 优先使用 get_strategy_info().parameters，其次使用 instance.parameters
        params = {}
        if hasattr(instance, 'get_strategy_info'):
            try:
                info = instance.get_strategy_info()
                params = (info or {}).get('parameters') or {}
            except Exception:
                params = {}
        if not params:
            params = getattr(instance, 'parameters', {}) or {}

        # 构建规范列表：name/type/default
        def infer_type(v):
            if isinstance(v, bool):
                return 'boolean'
            if isinstance(v, int):
                return 'integer'
            if isinstance(v, float):
                return 'float'
            if isinstance(v, str):
                return 'string'
            if isinstance(v, list):
                return 'list'
            if isinstance(v, dict):
                return 'dict'
            return 'unknown'

        spec = []
        for k, v in params.items():
            spec.append({
                "name": k,
                "type": infer_type(v),
                "default": v
            })

        return {"status": "success", "data": spec}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"自动提取策略参数失败: {e}")
        raise HTTPException(status_code=500, detail=f"自动提取策略参数失败: {str(e)}")


class ParameterSetRequest(BaseModel):
    strategy_id: int
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    status: Optional[str] = 'active'


@router.get("/strategies/{strategy_id}/parameter-spaces")
async def get_parameter_spaces(
    strategy_id: int,
    db: Session = Depends(get_db)
):
    try:
        spaces = db.query(StrategyParameterSpace).filter(
            StrategyParameterSpace.strategy_id == strategy_id
        ).all()
        return {"status": "success", "data": [
            {
                "id": s.id,
                "parameter_name": s.parameter_name,
                "parameter_type": s.parameter_type,
                "min_value": s.min_value,
                "max_value": s.max_value,
                "step_size": s.step_size,
                "choices": s.choices,
                "description": s.description
            } for s in spaces
        ]}
    except Exception as e:
        logger.exception("Failed to get parameter spaces")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/{strategy_id}/parameter-spaces")
async def create_parameter_spaces(
    strategy_id: int,
    spaces: List[ParameterSpaceRequest],
    db: Session = Depends(get_db)
):
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        # remove existing spaces
        db.query(StrategyParameterSpace).filter(StrategyParameterSpace.strategy_id == strategy_id).delete()
        for sp in spaces:
            rec = StrategyParameterSpace(
                strategy_id=strategy_id,
                parameter_name=sp.parameter_name,
                parameter_type=sp.parameter_type,
                min_value=sp.min_value,
                max_value=sp.max_value,
                step_size=sp.step_size,
                choices=sp.choices,
                description=sp.description
            )
            db.add(rec)
        db.commit()
        return {"status": "success", "message": f"created {len(spaces)} parameter spaces"}
    except Exception as e:
        db.rollback()
        logger.exception("Failed to create parameter spaces")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize")
async def start_optimization(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        strategy = db.query(Strategy).filter(Strategy.id == request.strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        job = OptimizationJob(
            strategy_id=request.strategy_id,
            name=request.name,
            description=request.description,
            optimization_config={
                "parameter_spaces": [s.dict() for s in request.parameter_spaces],
                "objective_function": request.objective_function,
                "n_trials": request.n_trials,
                "timeout": request.timeout,
                "backtest_config": request.backtest_config
            },
            objective_function=request.objective_function,
            total_trials=request.n_trials,
            status='running',
            started_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # schedule the blocking optimization to run in a thread
        background_tasks.add_task(asyncio.to_thread, _run_optimization_worker, job.id)

        return {"status": "success", "data": {"job_id": job.id, "message": "optimization started"}}
    except Exception as e:
        db.rollback()
        logger.exception("Failed to start optimization")
        raise HTTPException(status_code=500, detail=str(e))


def _run_optimization_worker(job_id: int):
    """Worker that runs inside a separate thread. It must create its own DB session."""
    db = None
    try:
        from ..optimization.optimizer import StrategyOptimizer
        db = SessionLocal()
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        logger.info(f"Starting optimization job {job.id} in background thread")
        optimizer = StrategyOptimizer(db, job)
        best_params, best_score = optimizer.optimize()

        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        job.status = 'completed'
        job.best_parameters = best_params
        job.best_score = best_score
        job.completed_at = datetime.utcnow()
        job.progress = 100.0
        db.commit()

        if best_params:
            ps = ParameterSet(
                strategy_id=job.strategy_id,
                name=f"{job.name}_best",
                description=f"Best params from optimization {job.name}",
                parameters=best_params,
                optimization_job_id=job.id,
                status='active'
            )
            db.add(ps)
            db.commit()

        logger.info(f"Optimization job {job.id} finished with score {best_score}")
    except Exception as e:
        logger.exception(f"Optimization job {job_id} failed: {e}")
        try:
            if db is None:
                db = SessionLocal()
            job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                db.commit()
        finally:
            if db:
                db.close()


@router.get("/jobs/{job_id}")
async def get_optimization_job(job_id: int, db: Session = Depends(get_db)):
    try:
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"status": "success", "data": {
            "id": job.id,
            "strategy_id": job.strategy_id,
            "name": job.name,
            "description": job.description,
            "status": job.status,
            "progress": job.progress,
            "best_score": job.best_score,
            "best_parameters": job.best_parameters,
            "objective_function": job.objective_function,
            "optimization_config": job.optimization_config,
            "total_trials": job.total_trials,
            "completed_trials": job.completed_trials,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message
        }}
    except Exception as e:
        logger.exception("Failed to get job")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_optimization_jobs(
    strategy_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(OptimizationJob)
        if strategy_id:
            query = query.filter(OptimizationJob.strategy_id == strategy_id)
        if status:
            query = query.filter(OptimizationJob.status == status)
        total = query.count()
        jobs = query.offset((page - 1) * size).limit(size).all()
        items = []
        for j in jobs:
            item = {
                "id": j.id,
                "strategy_id": j.strategy_id,
                "name": j.name,
                "status": j.status,
                "progress": _json_safe(j.progress),
                "best_score": _json_safe(j.best_score),
                "best_parameters": _sanitize_for_json(j.best_parameters) if j.best_parameters else None,
                "optimization_config": _sanitize_for_json(j.optimization_config) if j.optimization_config else None,
                "objective_function": j.objective_function,
                "total_trials": j.total_trials,
                "completed_trials": j.completed_trials,
                "created_at": j.created_at.isoformat() if j.created_at else None
            }
            items.append(item)
        return {"status": "success", "data": {
            "total": total,
            "page": page,
            "size": size,
            "jobs": items
        }}
    except Exception as e:
        logger.exception("Failed to list jobs")
        raise HTTPException(status_code=500, detail=str(e))


# 移除重复且错误的试验列表路由，使用下方的标准实现(`/jobs/{job_id}/trials`)


@router.post("/strategies/{strategy_id}/parameter-spaces")
async def create_parameter_spaces(
    strategy_id: int,
    spaces: List[ParameterSpaceRequest],
    db: Session = Depends(get_db)
):
    """创建或更新策略的参数空间定义"""
    try:
        # 检查策略是否存在
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        # 删除现有的参数空间定义
        db.query(StrategyParameterSpace).filter(
            StrategyParameterSpace.strategy_id == strategy_id
        ).delete()
        
        # 创建新的参数空间定义
        created_spaces = []
        for space_req in spaces:
            space = StrategyParameterSpace(
                strategy_id=strategy_id,
                parameter_name=space_req.parameter_name,
                parameter_type=space_req.parameter_type,
                min_value=space_req.min_value,
                max_value=space_req.max_value,
                step_size=space_req.step_size,
                choices=space_req.choices,
                description=space_req.description
            )
            db.add(space)
            created_spaces.append(space)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"成功创建{len(created_spaces)}个参数空间定义"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"创建参数空间失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建参数空间失败: {str(e)}")


@router.post("/optimize")
async def start_optimization(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """启动参数优化任务"""
    try:
        # 检查策略是否存在
        strategy = db.query(Strategy).filter(Strategy.id == request.strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        # 创建优化任务记录
        job = OptimizationJob(
            strategy_id=request.strategy_id,
            name=request.name,
            description=request.description,
            optimization_config={
                "parameter_spaces": [space.dict() for space in request.parameter_spaces],
                "objective_function": request.objective_function,
                "n_trials": request.n_trials,
                "timeout": request.timeout,
                "backtest_config": request.backtest_config
            },
            objective_function=request.objective_function,
            total_trials=request.n_trials,
            status='running',
            started_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # 启动后台优化任务（在独立线程运行，避免阻塞主事件循环或复用请求会话）
        background_tasks.add_task(run_optimization, job.id)

        return {
            "status": "success",
            "data": {
                "job_id": job.id,
                "message": "优化任务已启动"
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"启动优化任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动优化任务失败: {str(e)}")


@router.get("/jobs/{job_id}")
async def get_optimization_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """获取优化任务详情"""
    try:
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="优化任务不存在")
        
        
        return {
            "status": "success",
            "data": {
                "id": job.id,
                "strategy_id": job.strategy_id,
                "name": job.name,
                "description": job.description,
                "status": job.status,
                "progress": job.progress,
                "best_score": job.best_score,
                "best_parameters": job.best_parameters,
                "objective_function": job.objective_function,
                "optimization_config": job.optimization_config,  # 添加优化配置
                "total_trials": job.total_trials,
                "completed_trials": job.completed_trials,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message
            }
        }
    except Exception as e:
        logger.error(f"获取优化任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取优化任务失败: {str(e)}")


@router.get("/jobs")
async def list_optimization_jobs(
    strategy_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List optimization jobs with pagination."""
    try:
        query = db.query(OptimizationJob)
        if strategy_id is not None:
            query = query.filter(OptimizationJob.strategy_id == strategy_id)
        if status:
            query = query.filter(OptimizationJob.status == status)

        total = query.count()
        jobs = query.offset((page - 1) * size).limit(size).all()

        items = []
        for j in jobs:
            items.append({
                "id": j.id,
                "strategy_id": j.strategy_id,
                "name": j.name,
                "status": j.status,
                "progress": _json_safe(j.progress),
                "best_score": _json_safe(j.best_score),
                "best_parameters": _sanitize_for_json(j.best_parameters) if j.best_parameters else None,
                "optimization_config": _sanitize_for_json(j.optimization_config) if j.optimization_config else None,
                "objective_function": j.objective_function,
                "total_trials": j.total_trials,
                "completed_trials": j.completed_trials,
                "created_at": j.created_at.isoformat() if j.created_at else None
            })

        return {"status": "success", "data": {
            "total": total,
            "page": page,
            "size": size,
            "jobs": items
        }}
    except Exception as e:
        logger.exception("Failed to list jobs")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/trials")
async def get_optimization_trials(
    job_id: int,
    db: Session = Depends(get_db)
):
    """获取优化任务的所有试验记录"""
    try:
        # 检查任务是否存在
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="优化任务不存在")
        
        # 获取所有试验记录，按得分降序排列
        trials = db.query(OptimizationTrial)\
            .filter(OptimizationTrial.job_id == job_id)\
            .filter(OptimizationTrial.status == 'completed')\
            .order_by(OptimizationTrial.objective_value.desc())\
            .all()
        
        return {
            "status": "success",
            "data": [
                {
                    "id": trial.id,
                    "trial_number": trial.trial_number,
                    "parameters": trial.parameters,
                    "objective_value": trial.objective_value,
                    "backtest_results": trial.backtest_results,  # 包含完整的回测结果
                    "status": trial.status,
                    "execution_time": trial.execution_time,
                    "created_at": trial.created_at.isoformat() if trial.created_at else None,
                    "completed_at": trial.completed_at.isoformat() if trial.completed_at else None
                }
                for trial in trials
            ]
        }
    except Exception as e:
        logger.error(f"获取优化试验列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取优化试验列表失败: {str(e)}")


@router.get("/jobs/{job_id}/trials-summary")
async def get_trials_summary(
    job_id: int,
    db: Session = Depends(get_db)
):
    """获取优化任务的试验摘要（轻量级，只包含关键指标）"""
    try:
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="优化任务不存在")
        
        trials = db.query(OptimizationTrial)\
            .filter(OptimizationTrial.job_id == job_id)\
            .filter(OptimizationTrial.status == 'completed')\
            .order_by(OptimizationTrial.objective_value.desc())\
            .all()
        
        trials_summary = []
        for i, trial in enumerate(trials):
            if trial.backtest_results:
                backtest_results = trial.backtest_results
                summary = {
                    "rank": i + 1,
                    "trial_number": trial.trial_number,
                    "objective_value": trial.objective_value,
                    "parameters": trial.parameters,
                    "execution_time": trial.execution_time,
                    "completed_at": trial.completed_at.isoformat() if trial.completed_at else None,
                    # 只包含关键性能指标，不包含详细数据
                    "total_return": backtest_results.get("total_return"),
                    "annual_return": backtest_results.get("annual_return"),
                    "sharpe_ratio": backtest_results.get("sharpe_ratio"),
                    "max_drawdown": backtest_results.get("max_drawdown"),
                    "total_trades": len(backtest_results.get("trades", []))
                }
                trials_summary.append(summary)
        
        return {
            "status": "success",
            "data": trials_summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取试验摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取试验摘要失败: {str(e)}")

@router.get("/jobs/{job_id}/best-performance")
async def get_best_performance(
    job_id: int,
    db: Session = Depends(get_db)
):
    """获取优化任务最佳试验的性能指标（轻量级，不包含详细数据）"""
    try:
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="优化任务不存在")
        
        # 获取最佳试验
        best_trial = db.query(OptimizationTrial)\
            .filter(OptimizationTrial.job_id == job_id)\
            .filter(OptimizationTrial.status == 'completed')\
            .order_by(OptimizationTrial.objective_value.desc())\
            .first()
        
        if not best_trial or not best_trial.backtest_results:
            raise HTTPException(status_code=404, detail="没有找到完整的回测结果")
        
        # 只返回关键的性能指标，不返回详细的交易记录和权益曲线
        backtest_results = best_trial.backtest_results
        performance_summary = {
            "total_return": backtest_results.get("total_return"),
            "annual_return": backtest_results.get("annual_return"), 
            "sharpe_ratio": backtest_results.get("sharpe_ratio"),
            "max_drawdown": backtest_results.get("max_drawdown"),
            "win_rate": backtest_results.get("win_rate"),
            "profit_factor": backtest_results.get("profit_factor"),
            "alpha": backtest_results.get("alpha"),
            "beta": backtest_results.get("beta"),
            # 添加交易统计但不包含详细记录
            "total_trades": len(backtest_results.get("trades", [])),
            "parameters": best_trial.parameters,
            "trial_number": best_trial.trial_number,
            "objective_value": best_trial.objective_value
        }
        
        return {
            "status": "success",
            "data": performance_summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最佳性能指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取最佳性能指标失败: {str(e)}")

@router.delete("/jobs/{job_id}")
async def delete_optimization_job(
    job_id: int,
    force: bool = Query(False, description="是否强制删除运行中的任务"),
    db: Session = Depends(get_db)
):
    """删除优化任务"""
    try:
        # 检查任务是否存在
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="优化任务不存在")
        
        # 检查任务状态，运行中的任务不能删除（除非强制删除）
        if job.status == 'running' and not force:
            raise HTTPException(status_code=400, detail="运行中的任务不能删除，请先停止任务")
        
        # 如果是强制删除运行中的任务，记录日志
        if job.status == 'running' and force:
            logger.warning(f"强制删除运行中的优化任务: ID={job_id}, 名称={job.name}")
        
        logger.info(f"删除优化任务: ID={job_id}, 名称={job.name}")
        
        # 删除相关的试验记录（级联删除）
        trials_count = db.query(OptimizationTrial).filter(OptimizationTrial.job_id == job_id).count()
        
        # 删除任务（会级联删除相关的试验记录）
        db.delete(job)
        db.commit()
        
        logger.info(f"成功删除优化任务 {job_id}，同时删除了 {trials_count} 个试验记录")
        
        return {
            "status": "success",
            "message": f"成功删除优化任务 '{job.name}' 及其 {trials_count} 个试验记录"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除优化任务失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除优化任务失败: {str(e)}")


@router.post("/parameter-sets")
async def create_parameter_set(
    request: ParameterSetRequest,
    db: Session = Depends(get_db)
):
    """创建参数组"""
    try:
        # 检查策略是否存在
        strategy = db.query(Strategy).filter(Strategy.id == request.strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        parameter_set = ParameterSet(
            strategy_id=request.strategy_id,
            name=request.name,
            description=request.description,
            parameters=request.parameters,
            status=request.status
        )
        db.add(parameter_set)
        db.commit()
        db.refresh(parameter_set)
        
        return {
            "status": "success",
            "data": {
                "id": parameter_set.id,
                "message": "参数组创建成功"
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"创建参数组失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建参数组失败: {str(e)}")


@router.get("/parameter-sets")
async def list_parameter_sets(
    strategy_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取参数组列表"""
    try:
        query = db.query(ParameterSet)
        
        if strategy_id:
            query = query.filter(ParameterSet.strategy_id == strategy_id)
        if status:
            query = query.filter(ParameterSet.status == status)
        
        total = query.count()
        parameter_sets = query.offset((page - 1) * size).limit(size).all()
        
        result = []
        for ps in parameter_sets:
            # 获取最新性能数据
            latest_performance = db.query(ParameterSetPerformance).filter(
                ParameterSetPerformance.parameter_set_id == ps.id
            ).order_by(ParameterSetPerformance.created_at.desc()).first()
            
            result.append({
                "id": ps.id,
                "strategy_id": ps.strategy_id,
                "name": ps.name,
                "description": ps.description,
                "parameters": ps.parameters,
                "status": ps.status,
                "is_default": ps.is_default,
                "created_at": ps.created_at.isoformat() if ps.created_at else None,
                "latest_performance": {
                    "total_return": latest_performance.total_return,
                    "annual_return": latest_performance.annual_return,
                    "max_drawdown": latest_performance.max_drawdown,
                    "sharpe_ratio": latest_performance.sharpe_ratio,
                    "ranking": latest_performance.ranking,
                    "backtest_date": latest_performance.backtest_date.isoformat() if latest_performance.backtest_date else None
                } if latest_performance else None
            })
        
        return {
            "status": "success",
            "data": result,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
    except Exception as e:
        logger.error(f"获取参数组列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取参数组列表失败: {str(e)}")


async def run_optimization(job_id: int):
    """运行参数优化的后台任务（将实际工作委托到线程，线程内创建独立 DB 会话）"""
    import optuna
    from ..optimization.optimizer import StrategyOptimizer

    def _sync_run(job_id_inner: int):
        db = SessionLocal()
        try:
            job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id_inner).first()
            if not job:
                logger.error(f"优化任务{job_id_inner}不存在")
                return

            logger.info(f"开始执行优化任务(线程): {job.name}")

            # 在该线程/会话中创建优化器并执行同步优化（optuna 运行是阻塞的）
            optimizer = StrategyOptimizer(db, job)
            best_params, best_score = optimizer.optimize()

            # 更新任务状态
            job.status = 'completed'
            job.best_parameters = best_params
            job.best_score = best_score
            job.completed_at = datetime.utcnow()
            job.progress = 100.0
            db.commit()

            # 创建最优参数组
            if best_params:
                parameter_set = ParameterSet(
                    strategy_id=job.strategy_id,
                    name=f"{job.name}_最优参数",
                    description=f"优化任务{job.name}的最优参数组合",
                    parameters=best_params,
                    optimization_job_id=job.id,
                    status='active'
                )
                db.add(parameter_set)
                db.commit()

                logger.info(f"优化任务{job.name}完成，最优得分: {best_score}")

        except Exception as e:
            logger.exception(f"优化任务{job_id_inner}执行失败(线程): {str(e)}")
            # 更新任务状态为失败
            try:
                job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id_inner).first()
                if job:
                    job.status = 'failed'
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()

    # 将阻塞型优化任务放入线程执行，避免阻塞事件循环
    await asyncio.to_thread(_sync_run, job_id)

@router.get("/strategies/{strategy_id}/best-parameters")
async def get_best_parameters(
    strategy_id: int,
    db: Session = Depends(get_db)
):
    """获取策略的最佳参数（从已完成的优化任务中）"""
    try:
        # 查找该策略已完成的优化任务，按最佳得分排序
        jobs = db.query(OptimizationJob).filter(
            OptimizationJob.strategy_id == strategy_id,
            OptimizationJob.status == 'completed',
            OptimizationJob.best_parameters.isnot(None)
        ).order_by(OptimizationJob.best_score.desc()).all()
        
        if not jobs:
            return {
                "status": "success", 
                "data": [],
                "message": "该策略暂无优化结果"
            }
        
        result = []
        for job in jobs:
            result.append({
                "job_id": job.id,
                "job_name": job.name,
                "best_score": job.best_score,
                "best_parameters": job.best_parameters,
                "objective_function": job.objective_function,
                "total_trials": job.total_trials,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "description": job.description
            })
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.error(f"获取最佳参数失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取最佳参数失败: {str(e)}")

@router.get("/jobs/{job_id}/best-parameters")
async def get_job_best_parameters(
    job_id: int,
    db: Session = Depends(get_db)
):
    """获取特定优化任务的最佳参数"""
    try:
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="优化任务不存在")
        
        if job.status != 'completed':
            raise HTTPException(status_code=400, detail="优化任务尚未完成")
        
        if not job.best_parameters:
            raise HTTPException(status_code=400, detail="该任务暂无最佳参数")
        
        return {
            "status": "success",
            "data": {
                "job_id": job.id,
                "job_name": job.name,
                "strategy_id": job.strategy_id,
                "best_score": job.best_score,
                "best_parameters": job.best_parameters,
                "objective_function": job.objective_function,
                "total_trials": job.total_trials,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "description": job.description
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务最佳参数失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务最佳参数失败: {str(e)}")
def _json_safe(value):
    """Return a JSON-safe value: convert non-finite floats to None."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value

def _sanitize_for_json(obj):
    """Recursively sanitize dict/list for JSON serialization (NaN/Inf -> None)."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return _json_safe(obj)
