"""
参数优化相关的API路由
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models import (
    get_db, Strategy, StrategyParameterSpace, ParameterSet, 
    ParameterSetPerformance, OptimizationJob, OptimizationTrial
)
from .backtest_service import BacktestService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/optimization", tags=["optimization"])

# 请求和响应模型
class ParameterSpaceRequest(BaseModel):
    parameter_name: str
    parameter_type: str  # 'int', 'float', 'choice'
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
    objective_function: str = 'sharpe_ratio'  # 'sharpe_ratio', 'total_return', 'max_drawdown'
    n_trials: int = 100
    timeout: Optional[int] = 3600  # 超时时间(秒)
    backtest_config: Dict[str, Any]  # 回测配置

class ParameterSetRequest(BaseModel):
    strategy_id: int
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    status: str = 'active'

class ParameterSetUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


@router.get("/strategies/{strategy_id}/parameter-spaces")
async def get_parameter_spaces(
    strategy_id: int,
    db: Session = Depends(get_db)
):
    """获取策略的参数空间定义"""
    try:
        spaces = db.query(StrategyParameterSpace).filter(
            StrategyParameterSpace.strategy_id == strategy_id
        ).all()
        
        return {
            "status": "success",
            "data": [
                {
                    "id": space.id,
                    "parameter_name": space.parameter_name,
                    "parameter_type": space.parameter_type,
                    "min_value": space.min_value,
                    "max_value": space.max_value,
                    "step_size": space.step_size,
                    "choices": space.choices,
                    "description": space.description
                }
                for space in spaces
            ]
        }
    except Exception as e:
        logger.error(f"获取参数空间失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取参数空间失败: {str(e)}")


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
        
        # 启动后台优化任务
        background_tasks.add_task(run_optimization, job.id, db)
        
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
    """获取优化任务列表"""
    try:
        query = db.query(OptimizationJob)
        
        if strategy_id:
            query = query.filter(OptimizationJob.strategy_id == strategy_id)
        if status:
            query = query.filter(OptimizationJob.status == status)
        
        total = query.count()
        jobs = query.offset((page - 1) * size).limit(size).all()
        
        return {
            "status": "success",
            "data": [
                {
                    "id": job.id,
                    "strategy_id": job.strategy_id,
                    "name": job.name,
                    "status": job.status,
                    "progress": job.progress,
                    "best_score": job.best_score,
                    "best_parameters": job.best_parameters,
                    "objective_function": job.objective_function,
                    "optimization_config": job.optimization_config,  # 添加优化配置
                    "total_trials": job.total_trials,
                    "completed_trials": job.completed_trials,
                    "created_at": job.created_at.isoformat() if job.created_at else None
                }
                for job in jobs
            ],
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
    except Exception as e:
        logger.error(f"获取优化任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取优化任务列表失败: {str(e)}")


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


async def run_optimization(job_id: int, db: Session):
    """运行参数优化的后台任务"""
    try:
        import optuna
        from ..optimization.optimizer import StrategyOptimizer
        
        # 获取任务信息
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if not job:
            logger.error(f"优化任务{job_id}不存在")
            return
        
        logger.info(f"开始执行优化任务: {job.name}")
        
        # 创建优化器
        optimizer = StrategyOptimizer(db, job)
        
        # 执行优化
        best_params, best_score = await optimizer.optimize()
        
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
        logger.error(f"优化任务{job_id}执行失败: {str(e)}")
        
        # 更新任务状态为失败
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
