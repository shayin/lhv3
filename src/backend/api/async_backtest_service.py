"""
异步回测服务
支持异步回测任务的提交、监控和管理
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session

from .backtest_service import BacktestService
from ..utils.task_queue import get_task_queue, TaskType, TaskResult
from ..models.optimization import OptimizationJob

logger = logging.getLogger(__name__)


class AsyncBacktestService:
    """异步回测服务"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化异步回测服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.backtest_service = BacktestService(db)
        self.task_queue = get_task_queue()
    
    async def submit_backtest_task(
        self,
        strategy_id: Union[str, int],
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0015,
        slippage_rate: float = 0.001,
        data_source: str = "database",
        parameters: Optional[Dict[str, Any]] = None,
        features: Optional[List[str]] = None,
        force_refresh: bool = False,
        task_name: Optional[str] = None,
        priority: int = 0
    ) -> str:
        """
        提交异步回测任务
        
        Args:
            strategy_id: 策略ID
            symbol: 交易品种
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            commission_rate: 手续费率
            slippage_rate: 滑点率
            data_source: 数据源
            parameters: 策略参数
            features: 技术指标
            force_refresh: 强制刷新缓存
            task_name: 任务名称
            priority: 优先级
            
        Returns:
            str: 任务ID
        """
        # 生成任务名称
        if task_name is None:
            task_name = f"回测_{symbol}_{strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 准备任务参数
        task_kwargs = {
            'strategy_id': strategy_id,
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'commission_rate': commission_rate,
            'slippage_rate': slippage_rate,
            'data_source': data_source,
            'parameters': parameters,
            'features': features,
            'force_refresh': force_refresh
        }
        
        # 任务元数据
        metadata = {
            'task_name': task_name,
            'task_type': 'backtest',
            'strategy_id': strategy_id,
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital
        }
        
        # 提交任务
        task_id = await self.task_queue.submit_task(
            task_type=TaskType.BACKTEST,
            func=self._run_backtest_sync,
            priority=priority,
            callback=self._backtest_callback,
            metadata=metadata,
            **task_kwargs
        )
        
        logger.info(f"异步回测任务已提交: {task_id} - {task_name}")
        
        return task_id
    
    def _run_backtest_sync(self, **kwargs) -> Dict[str, Any]:
        """
        同步执行回测（在线程池中运行）
        
        Args:
            **kwargs: 回测参数
            
        Returns:
            Dict[str, Any]: 回测结果
        """
        try:
            logger.info(f"开始执行回测任务，参数: {kwargs}")
            
            # 创建新的数据库会话（线程安全）
            from ..models.base import SessionLocal
            db = SessionLocal()
            
            try:
                # 创建回测服务实例
                backtest_service = BacktestService(db)
                
                # 执行回测
                result = backtest_service.run_backtest(**kwargs)
                
                logger.info(f"回测任务执行成功")
                return result
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"回测执行失败: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "data": None
            }
    
    async def _backtest_callback(self, result: TaskResult):
        """
        回测完成回调
        
        Args:
            result: 任务结果
        """
        try:
            task_id = result.task_id
            
            if result.status.value == "completed":
                logger.info(f"回测任务 {task_id} 完成")
                
                # 可以在这里添加额外的处理逻辑
                # 例如：发送通知、更新数据库等
                
            elif result.status.value == "failed":
                logger.error(f"回测任务 {task_id} 失败: {result.error}")
                
        except Exception as e:
            logger.error(f"回测回调处理失败: {e}")
    
    async def submit_batch_backtest_tasks(
        self,
        backtest_configs: List[Dict[str, Any]],
        priority: int = 0
    ) -> List[str]:
        """
        批量提交回测任务
        
        Args:
            backtest_configs: 回测配置列表
            priority: 优先级
            
        Returns:
            List[str]: 任务ID列表
        """
        task_ids = []
        
        for i, config in enumerate(backtest_configs):
            # 为批量任务设置递减优先级
            task_priority = priority - i
            
            # 从config中移除priority参数，避免重复
            config_copy = config.copy()
            config_copy.pop('priority', None)
            
            task_id = await self.submit_backtest_task(
                priority=task_priority,
                **config_copy
            )
            task_ids.append(task_id)
        
        logger.info(f"批量提交了 {len(task_ids)} 个回测任务")
        
        return task_ids
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务状态信息
        """
        try:
            result = self.task_queue.get_task_status(task_id)
            
            if result is None:
                return None
            
            # 如果result已经是字典格式，直接返回
            if isinstance(result, dict):
                return result
            
            # 如果result是TaskResult对象，转换为字典
            return {
                'task_id': result.task_id,
                'status': result.status.value,
                'progress': result.progress,
                'result': result.result,
                'error': result.error,
                'created_at': result.created_at.isoformat() if result.created_at else None,
                'started_at': result.started_at.isoformat() if result.started_at else None,
                'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                'metadata': result.metadata
            }
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}", exc_info=True)
            return None
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有任务状态
        
        Returns:
            List[Dict[str, Any]]: 所有任务状态列表
        """
        all_results = self.task_queue.get_all_tasks()
        
        tasks = []
        for task_id, result in all_results.items():
            # 只返回回测任务
            if result.metadata.get('task_type') == 'backtest':
                tasks.append({
                    'task_id': result.task_id,
                    'status': result.status.value,
                    'progress': result.progress,
                    'result': result.result,
                    'error': result.error,
                    'created_at': result.created_at.isoformat() if result.created_at else None,
                    'started_at': result.started_at.isoformat() if result.started_at else None,
                    'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                    'metadata': result.metadata
                })
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x['created_at'] or '', reverse=True)
        
        return tasks
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        return await self.task_queue.cancel_task(task_id)
    
    def get_queue_info(self) -> Dict[str, Any]:
        """
        获取队列信息
        
        Returns:
            Dict[str, Any]: 队列信息
        """
        running_tasks = self.task_queue.get_running_tasks()
        queue_size = self.task_queue.get_queue_size()
        
        # 统计回测任务
        backtest_running = sum(
            1 for task in running_tasks.values()
            if task.task_type == TaskType.BACKTEST
        )
        
        return {
            'queue_size': queue_size,
            'running_tasks': len(running_tasks),
            'backtest_running': backtest_running,
            'max_concurrent': self.task_queue.max_concurrent_tasks,
            'max_workers': self.task_queue.max_workers
        }


class AsyncOptimizationService:
    """异步参数优化服务"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化异步优化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.task_queue = get_task_queue()
    
    async def submit_optimization_task(
        self,
        job_id: int,
        priority: int = 0
    ) -> str:
        """
        提交异步优化任务
        
        Args:
            job_id: 优化任务ID
            priority: 优先级
            
        Returns:
            str: 任务ID
        """
        # 获取优化任务信息
        if self.db:
            job = self.db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
            if not job:
                raise ValueError(f"优化任务 {job_id} 不存在")
            
            task_name = f"优化_{job.name}_{job_id}"
        else:
            task_name = f"优化任务_{job_id}"
        
        # 任务元数据
        metadata = {
            'task_name': task_name,
            'task_type': 'optimization',
            'job_id': job_id
        }
        
        # 提交任务
        task_id = await self.task_queue.submit_task(
            task_type=TaskType.OPTIMIZATION,
            func=self._run_optimization_sync,
            job_id=job_id,
            priority=priority,
            callback=self._optimization_callback,
            metadata=metadata
        )
        
        logger.info(f"异步优化任务已提交: {task_id} - {task_name}")
        
        return task_id
    
    def _run_optimization_sync(self, job_id: int) -> Dict[str, Any]:
        """
        同步执行优化（在线程池中运行）
        
        Args:
            job_id: 优化任务ID
            
        Returns:
            Dict[str, Any]: 优化结果
        """
        try:
            # 创建新的数据库会话（线程安全）
            from ..models.base import SessionLocal
            from ..optimization.optimizer import StrategyOptimizer
            
            db = SessionLocal()
            
            try:
                # 获取优化任务
                job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
                if not job:
                    raise ValueError(f"优化任务 {job_id} 不存在")
                
                # 创建优化器并执行
                optimizer = StrategyOptimizer(db, job)
                best_params, best_score = optimizer.optimize()
                
                # 更新任务状态
                job.status = 'completed'
                job.best_parameters = best_params
                job.best_score = best_score
                job.completed_at = datetime.utcnow()
                job.progress = 100.0
                db.commit()
                
                return {
                    'status': 'success',
                    'best_parameters': best_params,
                    'best_score': best_score,
                    'job_id': job_id
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"优化执行失败: {e}")
            
            # 更新任务状态为失败
            try:
                from ..models.base import SessionLocal
                db = SessionLocal()
                job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
                if job:
                    job.status = 'failed'
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    db.commit()
                db.close()
            except Exception:
                pass
            
            return {
                'status': 'error',
                'message': str(e),
                'job_id': job_id
            }
    
    async def _optimization_callback(self, result: TaskResult):
        """
        优化完成回调
        
        Args:
            result: 任务结果
        """
        try:
            task_id = result.task_id
            job_id = result.metadata.get('job_id')
            
            if result.status.value == "completed":
                logger.info(f"优化任务 {task_id} (job_id: {job_id}) 完成")
                
            elif result.status.value == "failed":
                logger.error(f"优化任务 {task_id} (job_id: {job_id}) 失败: {result.error}")
                
        except Exception as e:
            logger.error(f"优化回调处理失败: {e}")
    
    def get_optimization_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有优化任务状态
        
        Returns:
            List[Dict[str, Any]]: 优化任务状态列表
        """
        all_results = self.task_queue.get_all_tasks()
        
        tasks = []
        for task_id, result in all_results.items():
            # 只返回优化任务
            if result.metadata.get('task_type') == 'optimization':
                tasks.append({
                    'task_id': result.task_id,
                    'status': result.status.value,
                    'progress': result.progress,
                    'result': result.result,
                    'error': result.error,
                    'created_at': result.created_at.isoformat() if result.created_at else None,
                    'started_at': result.started_at.isoformat() if result.started_at else None,
                    'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                    'metadata': result.metadata
                })
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x['created_at'] or '', reverse=True)
        
        return tasks