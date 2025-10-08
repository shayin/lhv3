"""
异步任务API路由
支持异步回测和优化任务的提交、监控和管理
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..models.data_models import get_db
from .async_backtest_service import AsyncBacktestService, AsyncOptimizationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/async", tags=["异步任务"])


# 请求模型
class BacktestTaskRequest(BaseModel):
    """回测任务请求"""
    strategy_id: str = Field(..., description="策略ID")
    symbol: str = Field(..., description="交易品种")
    start_date: str = Field(..., description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    initial_capital: float = Field(100000.0, description="初始资金")
    commission_rate: float = Field(0.0015, description="手续费率")
    slippage_rate: float = Field(0.001, description="滑点率")
    data_source: str = Field("database", description="数据源")
    parameters: Optional[Dict[str, Any]] = Field(None, description="策略参数")
    features: Optional[List[str]] = Field(None, description="技术指标")
    force_refresh: bool = Field(False, description="强制刷新缓存")
    task_name: Optional[str] = Field(None, description="任务名称")
    priority: int = Field(0, description="优先级")


class BatchBacktestTaskRequest(BaseModel):
    """批量回测任务请求"""
    backtest_configs: List[BacktestTaskRequest] = Field(..., description="回测配置列表")
    priority: int = Field(0, description="优先级")


class OptimizationTaskRequest(BaseModel):
    """优化任务请求"""
    job_id: int = Field(..., description="优化任务ID")
    priority: int = Field(0, description="优先级")


# 响应模型
class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="响应消息")


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress: float = Field(..., description="进度百分比")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: Optional[str] = Field(None, description="创建时间")
    started_at: Optional[str] = Field(None, description="开始时间")
    completed_at: Optional[str] = Field(None, description="完成时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="任务元数据")


class QueueInfoResponse(BaseModel):
    """队列信息响应"""
    queue_size: int = Field(..., description="队列大小")
    running_tasks: int = Field(..., description="运行中任务数")
    backtest_running: int = Field(..., description="运行中回测任务数")
    max_concurrent: int = Field(..., description="最大并发数")
    max_workers: int = Field(..., description="最大工作线程数")


# 回测相关路由
@router.post("/backtest/submit", response_model=TaskResponse)
async def submit_backtest_task(
    request: BacktestTaskRequest,
    db: Session = Depends(get_db)
):
    """
    提交异步回测任务
    """
    try:
        service = AsyncBacktestService(db)
        
        task_id = await service.submit_backtest_task(
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            slippage_rate=request.slippage_rate,
            data_source=request.data_source,
            parameters=request.parameters,
            features=request.features,
            force_refresh=request.force_refresh,
            task_name=request.task_name,
            priority=request.priority
        )
        
        return TaskResponse(
            task_id=task_id,
            message=f"回测任务已提交，任务ID: {task_id}"
        )
        
    except Exception as e:
        logger.error(f"提交回测任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest/batch", response_model=Dict[str, Any])
async def submit_batch_backtest_tasks(
    request: BatchBacktestTaskRequest,
    db: Session = Depends(get_db)
):
    """
    批量提交回测任务
    """
    try:
        service = AsyncBacktestService(db)
        
        # 转换请求格式
        backtest_configs = []
        for config in request.backtest_configs:
            backtest_configs.append(config.dict())
        
        task_ids = await service.submit_batch_backtest_tasks(
            backtest_configs=backtest_configs,
            priority=request.priority
        )
        
        return {
            "task_ids": task_ids,
            "count": len(task_ids),
            "message": f"批量提交了 {len(task_ids)} 个回测任务"
        }
        
    except Exception as e:
        logger.error(f"批量提交回测任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/status/{task_id}", response_model=TaskStatusResponse)
async def get_backtest_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    获取回测任务状态
    """
    try:
        service = AsyncBacktestService(db)
        status = service.get_task_status(task_id)
        
        if status is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return TaskStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/result/{task_id}")
async def get_backtest_task_result(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    获取回测任务结果
    """
    try:
        service = AsyncBacktestService(db)
        status = service.get_task_status(task_id)
        
        if status is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 只有任务完成时才返回结果
        if status.get('status') != 'completed':
            raise HTTPException(status_code=404, detail="任务尚未完成")
        
        return status.get('result', {})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/tasks", response_model=List[TaskStatusResponse])
async def get_all_backtest_tasks(
    db: Session = Depends(get_db)
):
    """
    获取所有回测任务状态
    """
    try:
        service = AsyncBacktestService(db)
        tasks = service.get_all_tasks()
        
        return [TaskStatusResponse(**task) for task in tasks]
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backtest/cancel/{task_id}")
async def cancel_backtest_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    取消回测任务
    """
    try:
        service = AsyncBacktestService(db)
        success = await service.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在或无法取消")
        
        return {"message": f"任务 {task_id} 已取消"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 优化相关路由
@router.post("/optimization/submit", response_model=TaskResponse)
async def submit_optimization_task(
    request: OptimizationTaskRequest,
    db: Session = Depends(get_db)
):
    """
    提交异步优化任务
    """
    try:
        service = AsyncOptimizationService(db)
        
        task_id = await service.submit_optimization_task(
            job_id=request.job_id,
            priority=request.priority
        )
        
        return TaskResponse(
            task_id=task_id,
            message=f"优化任务已提交，任务ID: {task_id}"
        )
        
    except Exception as e:
        logger.error(f"提交优化任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization/tasks", response_model=List[TaskStatusResponse])
async def get_all_optimization_tasks(
    db: Session = Depends(get_db)
):
    """
    获取所有优化任务状态
    """
    try:
        service = AsyncOptimizationService(db)
        tasks = service.get_optimization_tasks()
        
        return [TaskStatusResponse(**task) for task in tasks]
        
    except Exception as e:
        logger.error(f"获取优化任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 队列管理路由
@router.get("/queue/info", response_model=QueueInfoResponse)
async def get_queue_info(
    db: Session = Depends(get_db)
):
    """
    获取任务队列信息
    """
    try:
        service = AsyncBacktestService(db)
        info = service.get_queue_info()
        
        return QueueInfoResponse(**info)
        
    except Exception as e:
        logger.error(f"获取队列信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/all", response_model=List[TaskStatusResponse])
async def get_all_tasks(
    task_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取所有任务状态
    
    Args:
        task_type: 任务类型过滤 (backtest, optimization)
    """
    try:
        backtest_service = AsyncBacktestService(db)
        optimization_service = AsyncOptimizationService(db)
        
        all_tasks = []
        
        if task_type is None or task_type == "backtest":
            backtest_tasks = backtest_service.get_all_tasks()
            all_tasks.extend(backtest_tasks)
        
        if task_type is None or task_type == "optimization":
            optimization_tasks = optimization_service.get_optimization_tasks()
            all_tasks.extend(optimization_tasks)
        
        # 按创建时间倒序排列
        all_tasks.sort(key=lambda x: x['created_at'] or '', reverse=True)
        
        return [TaskStatusResponse(**task) for task in all_tasks]
        
    except Exception as e:
        logger.error(f"获取所有任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/cancel/{task_id}")
async def cancel_any_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    取消任意类型的任务
    """
    try:
        # 尝试通过回测服务取消
        backtest_service = AsyncBacktestService(db)
        success = await backtest_service.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在或无法取消")
        
        return {"message": f"任务 {task_id} 已取消"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 健康检查
@router.get("/health")
async def health_check():
    """
    异步任务系统健康检查
    """
    try:
        from ..utils.task_queue import get_task_queue
        
        task_queue = get_task_queue()
        queue_info = {
            'queue_size': task_queue.get_queue_size(),
            'running_tasks': len(task_queue.get_running_tasks()),
            'max_concurrent': task_queue.max_concurrent_tasks,
            'max_workers': task_queue.max_workers
        }
        
        return {
            "status": "healthy",
            "message": "异步任务系统运行正常",
            "queue_info": queue_info
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "message": f"异步任务系统异常: {str(e)}"
        }