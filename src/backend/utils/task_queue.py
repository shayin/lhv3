"""
异步任务队列系统
支持回测和参数优化任务的并行执行
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import threading
import json

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """任务类型枚举"""
    BACKTEST = "backtest"
    OPTIMIZATION = "optimization"


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """任务定义"""
    task_id: str
    task_type: TaskType
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None
    priority: int = 0  # 优先级，数字越大优先级越高
    timeout: Optional[int] = None  # 超时时间（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class TaskQueue:
    """异步任务队列"""
    
    def __init__(self, max_workers: int = 4, max_concurrent_tasks: int = 10):
        """
        初始化任务队列
        
        Args:
            max_workers: 线程池最大工作线程数
            max_concurrent_tasks: 最大并发任务数
        """
        self.max_workers = max_workers
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # 任务队列和结果存储
        self._pending_tasks: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_tasks: Dict[str, Task] = {}
        self._task_results: Dict[str, TaskResult] = {}
        
        # 线程池执行器，优化线程池配置
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="task-worker"
        )
        
        # 控制并发的信号量
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        
        # 任务处理器
        self._worker_tasks: List[asyncio.Task] = []
        self._shutdown = False
        
        # 启动工作线程
        self._start_workers()
        
        logger.info(f"任务队列初始化完成: max_workers={max_workers}, max_concurrent_tasks={max_concurrent_tasks}")
    
    def _start_workers(self):
        """启动工作线程"""
        for i in range(self.max_workers):
            worker_task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._worker_tasks.append(worker_task)
    
    async def _worker(self, worker_name: str):
        """工作线程主循环"""
        logger.info(f"工作线程 {worker_name} 启动")
        
        while not self._shutdown:
            try:
                # 获取任务（带超时，避免无限等待）
                try:
                    priority, task = await asyncio.wait_for(
                        self._pending_tasks.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # 获取并发控制信号量
                async with self._semaphore:
                    await self._execute_task(task, worker_name)
                
            except Exception as e:
                logger.error(f"工作线程 {worker_name} 发生错误: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"工作线程 {worker_name} 停止")
    
    async def _execute_task(self, task: Task, worker_name: str):
        """执行单个任务"""
        task_id = task.task_id
        
        try:
            # 更新任务状态
            self._running_tasks[task_id] = task
            result = self._task_results[task_id]
            result.status = TaskStatus.RUNNING
            result.started_at = datetime.utcnow()
            
            logger.info(f"工作线程 {worker_name} 开始执行任务 {task_id} ({task.task_type.value})")
            
            # 在线程池中执行任务
            if asyncio.iscoroutinefunction(task.func):
                # 异步函数直接执行
                task_result = await task.func(*task.args, **task.kwargs)
            else:
                # 同步函数在线程池中执行
                loop = asyncio.get_event_loop()
                # 创建一个包装函数来正确传递参数
                def wrapper():
                    return task.func(*task.args, **task.kwargs)
                
                task_result = await loop.run_in_executor(
                    self._executor, wrapper
                )
            
            # 更新结果
            result.status = TaskStatus.COMPLETED
            result.result = task_result
            result.completed_at = datetime.utcnow()
            
            logger.info(f"任务 {task_id} 执行成功")
            
            # 执行回调
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(result)
                    else:
                        task.callback(result)
                except Exception as e:
                    logger.error(f"任务 {task_id} 回调执行失败: {e}")
            
        except Exception as e:
            # 任务执行失败
            result.status = TaskStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.utcnow()
            
            # 记录详细错误信息
            logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
            
        finally:
            # 清理运行中的任务
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
    
    async def submit_task(
        self,
        task_type: TaskType,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        priority: int = 0,
        timeout: Optional[int] = None,
        callback: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        提交任务到队列
        
        Args:
            task_type: 任务类型
            func: 要执行的函数
            *args: 函数参数
            task_id: 任务ID（可选，自动生成）
            priority: 优先级
            timeout: 超时时间
            callback: 完成回调
            metadata: 元数据
            **kwargs: 函数关键字参数
            
        Returns:
            str: 任务ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        if metadata is None:
            metadata = {}
        
        # 创建任务
        task = Task(
            task_id=task_id,
            task_type=task_type,
            func=func,
            args=args,
            kwargs=kwargs,
            callback=callback,
            priority=priority,
            timeout=timeout,
            metadata=metadata
        )
        
        # 创建任务结果
        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
            metadata=metadata
        )
        
        self._task_results[task_id] = result
        
        # 添加到队列（优先级队列，负数表示高优先级）
        await self._pending_tasks.put((-priority, task))
        
        logger.info(f"任务 {task_id} ({task_type.value}) 已提交到队列，优先级: {priority}")
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        result = self._task_results.get(task_id)
        if not result:
            return None
            
        # 计算进度百分比
        progress = result.progress
        if result.status == TaskStatus.COMPLETED:
            progress = 100.0
        elif result.status == TaskStatus.RUNNING:
            # 对于运行中的任务，可以根据执行时间估算进度
            if result.started_at:
                elapsed = (datetime.utcnow() - result.started_at).total_seconds()
                # 简单的进度估算（可以根据具体任务类型优化）
                progress = min(elapsed / 60.0 * 100, 95.0)  # 假设任务大约1分钟完成
        
        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "progress": progress,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "error": result.error,
            "result": result.result,
            "metadata": result.metadata
        }
    
    def get_all_tasks(self) -> Dict[str, TaskResult]:
        """获取所有任务状态"""
        return self._task_results.copy()
    
    def get_running_tasks(self) -> Dict[str, Task]:
        """获取正在运行的任务"""
        return self._running_tasks.copy()
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self._pending_tasks.qsize()
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        if task_id in self._task_results:
            result = self._task_results[task_id]
            
            if result.status == TaskStatus.PENDING:
                result.status = TaskStatus.CANCELLED
                result.completed_at = datetime.utcnow()
                logger.info(f"任务 {task_id} 已取消")
                return True
            elif result.status == TaskStatus.RUNNING:
                # 正在运行的任务较难取消，这里只标记状态
                # 实际的取消需要任务函数内部支持
                result.status = TaskStatus.CANCELLED
                result.completed_at = datetime.utcnow()
                logger.warning(f"任务 {task_id} 正在运行，已标记为取消")
                return True
        
        return False
    
    def clear_completed_tasks(self, keep_recent: int = 100):
        """
        清理已完成的任务
        
        Args:
            keep_recent: 保留最近的任务数量
        """
        completed_tasks = [
            (task_id, result) for task_id, result in self._task_results.items()
            if result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]
        
        # 按完成时间排序，保留最近的任务
        completed_tasks.sort(key=lambda x: x[1].completed_at or datetime.min, reverse=True)
        
        if len(completed_tasks) > keep_recent:
            to_remove = completed_tasks[keep_recent:]
            for task_id, _ in to_remove:
                del self._task_results[task_id]
            
            logger.info(f"清理了 {len(to_remove)} 个已完成的任务")
    
    async def shutdown(self):
        """关闭任务队列"""
        logger.info("开始关闭任务队列...")
        
        self._shutdown = True
        
        # 等待所有工作线程完成（最多等待30秒）
        if self._worker_tasks:
            logger.info(f"等待 {len(self._worker_tasks)} 个工作线程完成...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._worker_tasks, return_exceptions=True),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("等待工作线程完成超时，强制关闭")
        
        # 关闭线程池
        if self._executor:
            logger.info("关闭线程池...")
            self._executor.shutdown(wait=True)
            
        logger.info("任务队列已关闭")


# 全局任务队列实例
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """获取全局任务队列实例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue


async def init_task_queue(max_workers: int = 4, max_concurrent_tasks: int = 10):
    """初始化全局任务队列"""
    global _task_queue
    if _task_queue is not None:
        await _task_queue.shutdown()
    
    _task_queue = TaskQueue(max_workers=max_workers, max_concurrent_tasks=max_concurrent_tasks)
    logger.info("全局任务队列已初始化")


async def shutdown_task_queue():
    """关闭全局任务队列"""
    global _task_queue
    if _task_queue is not None:
        await _task_queue.shutdown()
        _task_queue = None