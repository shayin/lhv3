#!/usr/bin/env python3
"""
异步回测和参数优化系统测试脚本

测试异步任务队列的并发性能和资源隔离效果
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, List, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AsyncSystemTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """检查系统健康状态"""
        try:
            async with self.session.get(f"{self.base_url}/api/async/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"系统健康状态: {data}")
                    return True
                else:
                    logger.error(f"健康检查失败: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"健康检查异常: {e}")
            return False
    
    async def submit_backtest_task(self, task_config: Dict[str, Any]) -> str:
        """提交回测任务"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/async/backtest/submit",
                json=task_config
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    task_id = data.get("task_id")
                    logger.info(f"回测任务已提交: {task_id}")
                    return task_id
                else:
                    error_text = await response.text()
                    logger.error(f"提交回测任务失败: {response.status} - {error_text}")
                    return None
        except Exception as e:
            logger.error(f"提交回测任务异常: {e}")
            return None
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            async with self.session.get(
                f"{self.base_url}/api/async/backtest/status/{task_id}"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"获取任务状态失败: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"获取任务状态异常: {e}")
            return None
    
    async def get_queue_info(self) -> Dict[str, Any]:
        """获取队列信息"""
        try:
            async with self.session.get(f"{self.base_url}/api/async/queue/info") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"获取队列信息失败: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"获取队列信息异常: {e}")
            return None
    
    async def wait_for_task_completion(self, task_id: str, timeout: int = 300) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = await self.get_task_status(task_id)
            if status:
                task_status = status.get("status")
                if task_status in ["completed", "failed"]:
                    return status
                
                # 显示进度
                progress = status.get("progress", 0)
                logger.info(f"任务 {task_id} 进度: {progress:.1f}% (状态: {task_status})")
            
            await asyncio.sleep(2)  # 每2秒检查一次
        
        logger.warning(f"任务 {task_id} 等待超时")
        return None


async def test_single_backtest():
    """测试单个回测任务"""
    logger.info("=" * 50)
    logger.info("测试单个回测任务")
    logger.info("=" * 50)
    
    async with AsyncSystemTester() as tester:
        # 检查系统健康状态
        if not await tester.health_check():
            logger.error("系统不健康，跳过测试")
            return
        
        # 准备回测配置
        task_config = {
            "strategy_id": "1",
            "symbol": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000.0,
            "commission_rate": 0.0015,
            "slippage_rate": 0.001,
            "data_source": "database",
            "task_name": "单任务测试",
            "priority": 0
        }
        
        # 提交任务
        task_id = await tester.submit_backtest_task(task_config)
        if not task_id:
            logger.error("任务提交失败")
            return
        
        # 等待任务完成
        result = await tester.wait_for_task_completion(task_id)
        if result:
            logger.info(f"任务完成: {result['status']}")
            if result['status'] == 'completed':
                logger.info("✅ 单个回测任务测试通过")
            else:
                logger.error(f"❌ 任务失败: {result.get('error')}")
        else:
            logger.error("❌ 任务超时")


async def test_concurrent_backtests():
    """测试并发回测任务"""
    logger.info("=" * 50)
    logger.info("测试并发回测任务")
    logger.info("=" * 50)
    
    async with AsyncSystemTester() as tester:
        # 检查系统健康状态
        if not await tester.health_check():
            logger.error("系统不健康，跳过测试")
            return
        
        # 准备多个回测配置
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
        task_configs = []
        
        for i, symbol in enumerate(symbols):
            config = {
                "strategy_id": "1",
                "symbol": symbol,
                "start_date": "2023-01-01",
                "end_date": "2023-06-30",
                "initial_capital": 100000.0,
                "commission_rate": 0.0015,
                "slippage_rate": 0.001,
                "data_source": "database",
                "task_name": f"并发测试_{symbol}",
                "priority": i  # 不同优先级
            }
            task_configs.append(config)
        
        # 并发提交任务
        logger.info(f"并发提交 {len(task_configs)} 个回测任务...")
        start_time = time.time()
        
        tasks = []
        for config in task_configs:
            task = asyncio.create_task(tester.submit_backtest_task(config))
            tasks.append(task)
        
        task_ids = await asyncio.gather(*tasks)
        task_ids = [tid for tid in task_ids if tid is not None]
        
        submit_time = time.time() - start_time
        logger.info(f"任务提交完成，耗时: {submit_time:.2f}秒，成功提交: {len(task_ids)} 个")
        
        # 监控队列状态
        queue_info = await tester.get_queue_info()
        if queue_info:
            logger.info(f"队列状态: {queue_info}")
        
        # 等待所有任务完成
        logger.info("等待所有任务完成...")
        completion_tasks = []
        for task_id in task_ids:
            task = asyncio.create_task(tester.wait_for_task_completion(task_id))
            completion_tasks.append(task)
        
        results = await asyncio.gather(*completion_tasks)
        
        # 统计结果
        completed = sum(1 for r in results if r and r.get('status') == 'completed')
        failed = sum(1 for r in results if r and r.get('status') == 'failed')
        timeout = sum(1 for r in results if r is None)
        
        total_time = time.time() - start_time
        
        logger.info("=" * 30)
        logger.info("并发测试结果:")
        logger.info(f"总任务数: {len(task_ids)}")
        logger.info(f"完成: {completed}")
        logger.info(f"失败: {failed}")
        logger.info(f"超时: {timeout}")
        logger.info(f"总耗时: {total_time:.2f}秒")
        logger.info("=" * 30)
        
        if completed == len(task_ids):
            logger.info("✅ 并发回测任务测试通过")
        else:
            logger.warning("⚠️ 部分任务未成功完成")


async def test_resource_isolation():
    """测试资源隔离效果"""
    logger.info("=" * 50)
    logger.info("测试资源隔离效果")
    logger.info("=" * 50)
    
    async with AsyncSystemTester() as tester:
        # 检查系统健康状态
        if not await tester.health_check():
            logger.error("系统不健康，跳过测试")
            return
        
        # 提交高优先级任务
        high_priority_config = {
            "strategy_id": "1",
            "symbol": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000.0,
            "task_name": "高优先级任务",
            "priority": 10
        }
        
        # 提交低优先级任务
        low_priority_configs = []
        for i in range(3):
            config = {
                "strategy_id": "1",
                "symbol": f"STOCK_{i}",
                "start_date": "2023-01-01",
                "end_date": "2023-06-30",
                "initial_capital": 50000.0,
                "task_name": f"低优先级任务_{i}",
                "priority": -5
            }
            low_priority_configs.append(config)
        
        # 先提交低优先级任务
        logger.info("提交低优先级任务...")
        low_priority_tasks = []
        for config in low_priority_configs:
            task_id = await tester.submit_backtest_task(config)
            if task_id:
                low_priority_tasks.append(task_id)
        
        # 稍等一下，然后提交高优先级任务
        await asyncio.sleep(1)
        logger.info("提交高优先级任务...")
        high_priority_task = await tester.submit_backtest_task(high_priority_config)
        
        # 监控任务执行顺序
        all_tasks = low_priority_tasks + [high_priority_task]
        logger.info("监控任务执行顺序...")
        
        for _ in range(10):  # 监控10次
            queue_info = await tester.get_queue_info()
            if queue_info:
                logger.info(f"队列状态: 队列大小={queue_info['queue_size']}, 运行中={queue_info['running_tasks']}")
            
            # 检查各任务状态
            for i, task_id in enumerate(all_tasks):
                if task_id:
                    status = await tester.get_task_status(task_id)
                    if status:
                        task_name = status.get('metadata', {}).get('task_name', f'任务{i}')
                        logger.info(f"{task_name}: {status['status']} (进度: {status['progress']:.1f}%)")
            
            await asyncio.sleep(3)
        
        logger.info("✅ 资源隔离测试完成")


async def test_batch_submission():
    """测试批量任务提交"""
    logger.info("=" * 50)
    logger.info("测试批量任务提交")
    logger.info("=" * 50)
    
    async with AsyncSystemTester() as tester:
        # 检查系统健康状态
        if not await tester.health_check():
            logger.error("系统不健康，跳过测试")
            return
        
        # 准备批量配置
        batch_configs = []
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        for symbol in symbols:
            config = {
                "strategy_id": "1",
                "symbol": symbol,
                "start_date": "2023-01-01",
                "end_date": "2023-03-31",
                "initial_capital": 100000.0,
                "task_name": f"批量测试_{symbol}"
            }
            batch_configs.append(config)
        
        # 批量提交
        batch_request = {
            "backtest_configs": batch_configs,
            "priority": 5
        }
        
        try:
            async with tester.session.post(
                f"{tester.base_url}/api/async/backtest/batch",
                json=batch_request
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    task_ids = data.get("task_ids", [])
                    logger.info(f"批量提交成功: {len(task_ids)} 个任务")
                    
                    # 等待所有任务完成
                    completion_tasks = []
                    for task_id in task_ids:
                        task = asyncio.create_task(tester.wait_for_task_completion(task_id, timeout=120))
                        completion_tasks.append(task)
                    
                    results = await asyncio.gather(*completion_tasks)
                    completed = sum(1 for r in results if r and r.get('status') == 'completed')
                    
                    if completed == len(task_ids):
                        logger.info("✅ 批量任务提交测试通过")
                    else:
                        logger.warning(f"⚠️ 批量任务部分失败: {completed}/{len(task_ids)}")
                else:
                    error_text = await response.text()
                    logger.error(f"批量提交失败: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"批量提交异常: {e}")


async def main():
    """主测试函数"""
    logger.info("开始异步系统测试")
    logger.info("=" * 60)
    
    try:
        # 测试单个回测任务
        await test_single_backtest()
        await asyncio.sleep(2)
        
        # 测试并发回测任务
        await test_concurrent_backtests()
        await asyncio.sleep(2)
        
        # 测试资源隔离
        await test_resource_isolation()
        await asyncio.sleep(2)
        
        # 测试批量提交
        await test_batch_submission()
        
        logger.info("=" * 60)
        logger.info("所有测试完成")
        
    except Exception as e:
        logger.error(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())