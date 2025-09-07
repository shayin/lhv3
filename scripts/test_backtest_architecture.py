#!/usr/bin/env python3
"""
回测新架构测试脚本
测试 BacktestStatus 和 BacktestHistory 表的功能
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.models import get_engine, BacktestStatus, BacktestHistory, Strategy, StrategySnapshot
from src.backend.config import DATABASE_URL

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BacktestArchitectureTester:
    """回测架构测试器"""
    
    def __init__(self, db_url: str = None):
        """初始化测试器"""
        self.db_url = db_url or DATABASE_URL
        self.engine = create_engine(self.db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        
    def test_create_status_record(self) -> bool:
        """测试创建状态记录"""
        logger.info("测试创建状态记录...")
        
        try:
            with self.Session() as session:
                # 创建测试策略快照
                strategy_snapshot = StrategySnapshot(
                    strategy_id=1,
                    name="测试策略",
                    description="测试策略描述",
                    code="print('test')",
                    parameters='{"param1": "value1"}',
                    template="test_template"
                )
                session.add(strategy_snapshot)
                session.flush()
                
                # 创建状态记录
                status_record = BacktestStatus(
                    name="测试回测_001",
                    description="测试回测描述",
                    strategy_id=1,
                    strategy_snapshot_id=strategy_snapshot.id,
                    start_date=datetime.now() - timedelta(days=365),
                    end_date=datetime.now(),
                    initial_capital=100000.0,
                    instruments=["AAPL", "GOOGL"],
                    parameters={"param1": "value1"},
                    position_config={"max_position": 0.1},
                    results={"total_return": 0.15, "sharpe_ratio": 1.2},
                    equity_curve=[{"date": "2023-01-01", "value": 100000}],
                    trade_records=[{"date": "2023-01-01", "action": "buy", "symbol": "AAPL"}],
                    performance_metrics={"total_return": 0.15, "max_drawdown": -0.05},
                    status="completed",
                    completed_at=datetime.now()
                )
                
                session.add(status_record)
                session.commit()
                session.refresh(status_record)
                
                logger.info(f"状态记录创建成功: ID={status_record.id}")
                return True
                
        except Exception as e:
            logger.error(f"创建状态记录失败: {str(e)}")
            return False
    
    def test_create_history_record(self, status_id: int) -> bool:
        """测试创建历史记录"""
        logger.info(f"测试创建历史记录 (状态ID: {status_id})...")
        
        try:
            with self.Session() as session:
                # 创建历史记录
                history_record = BacktestHistory(
                    status_id=status_id,
                    start_date=datetime.now() - timedelta(days=200),
                    end_date=datetime.now() - timedelta(days=10),
                    initial_capital=100000.0,
                    instruments=["AAPL", "GOOGL"],
                    parameters={"param1": "value1_updated"},
                    position_config={"max_position": 0.15},
                    results={"total_return": 0.12, "sharpe_ratio": 1.1},
                    equity_curve=[{"date": "2023-01-01", "value": 100000}],
                    trade_records=[{"date": "2023-01-01", "action": "buy", "symbol": "AAPL"}],
                    performance_metrics={"total_return": 0.12, "max_drawdown": -0.03},
                    status="completed",
                    completed_at=datetime.now() - timedelta(days=10),
                    operation_type="update"
                )
                
                session.add(history_record)
                session.commit()
                session.refresh(history_record)
                
                logger.info(f"历史记录创建成功: ID={history_record.id}")
                return True
                
        except Exception as e:
            logger.error(f"创建历史记录失败: {str(e)}")
            return False
    
    def test_update_status_record(self, status_id: int) -> bool:
        """测试更新状态记录"""
        logger.info(f"测试更新状态记录 (ID: {status_id})...")
        
        try:
            with self.Session() as session:
                # 获取状态记录
                status_record = session.query(BacktestStatus).filter(BacktestStatus.id == status_id).first()
                if not status_record:
                    logger.error("状态记录不存在")
                    return False
                
                # 更新记录
                old_updated_at = status_record.updated_at
                status_record.description = "更新后的描述"
                status_record.performance_metrics = {"total_return": 0.18, "max_drawdown": -0.04}
                status_record.updated_at = datetime.now()
                
                session.commit()
                session.refresh(status_record)
                
                # 验证更新
                if status_record.description == "更新后的描述" and status_record.updated_at > old_updated_at:
                    logger.info("状态记录更新成功")
                    return True
                else:
                    logger.error("状态记录更新验证失败")
                    return False
                    
        except Exception as e:
            logger.error(f"更新状态记录失败: {str(e)}")
            return False
    
    def test_query_operations(self) -> bool:
        """测试查询操作"""
        logger.info("测试查询操作...")
        
        try:
            with self.Session() as session:
                # 测试基本查询
                status_count = session.query(BacktestStatus).count()
                history_count = session.query(BacktestHistory).count()
                
                logger.info(f"状态记录数: {status_count}")
                logger.info(f"历史记录数: {history_count}")
                
                # 测试关联查询
                status_with_history = session.query(BacktestStatus).join(BacktestHistory).distinct().count()
                logger.info(f"有历史记录的状态数: {status_with_history}")
                
                # 测试按名称查询
                test_status = session.query(BacktestStatus).filter(
                    BacktestStatus.name.like("%测试回测%")
                ).first()
                
                if test_status:
                    logger.info(f"找到测试状态记录: {test_status.name}")
                    
                    # 查询该状态的历史记录
                    history_records = session.query(BacktestHistory).filter(
                        BacktestHistory.status_id == test_status.id
                    ).order_by(BacktestHistory.created_at.desc()).all()
                    
                    logger.info(f"该状态的历史记录数: {len(history_records)}")
                    
                    for record in history_records:
                        logger.info(f"  历史记录 {record.id}: {record.operation_type} - {record.created_at}")
                
                return True
                
        except Exception as e:
            logger.error(f"查询操作失败: {str(e)}")
            return False
    
    def test_data_integrity(self) -> bool:
        """测试数据完整性"""
        logger.info("测试数据完整性...")
        
        try:
            with self.Session() as session:
                # 检查孤立的历史记录
                orphaned_history = session.execute("""
                    SELECT COUNT(*) FROM backtest_history h
                    LEFT JOIN backtest_status s ON h.status_id = s.id
                    WHERE s.id IS NULL
                """).scalar()
                
                if orphaned_history > 0:
                    logger.error(f"发现 {orphaned_history} 条孤立的历史记录")
                    return False
                
                # 检查状态记录是否有对应的历史记录
                status_without_history = session.execute("""
                    SELECT COUNT(*) FROM backtest_status s
                    LEFT JOIN backtest_history h ON s.id = h.status_id
                    WHERE h.id IS NULL
                """).scalar()
                
                if status_without_history > 0:
                    logger.warning(f"发现 {status_without_history} 个状态记录没有对应的历史记录")
                
                # 检查重复的状态记录名称
                duplicate_names = session.execute("""
                    SELECT name, COUNT(*) as count 
                    FROM backtest_status 
                    GROUP BY name 
                    HAVING COUNT(*) > 1
                """).fetchall()
                
                if duplicate_names:
                    logger.error(f"发现重复的状态记录名称: {duplicate_names}")
                    return False
                
                logger.info("数据完整性检查通过")
                return True
                
        except Exception as e:
            logger.error(f"数据完整性检查失败: {str(e)}")
            return False
    
    def test_performance(self) -> bool:
        """测试性能"""
        logger.info("测试查询性能...")
        
        try:
            import time
            
            with self.Session() as session:
                # 测试状态记录查询性能
                start_time = time.time()
                status_records = session.query(BacktestStatus).limit(100).all()
                status_query_time = time.time() - start_time
                
                # 测试历史记录查询性能
                start_time = time.time()
                history_records = session.query(BacktestHistory).limit(100).all()
                history_query_time = time.time() - start_time
                
                # 测试关联查询性能
                start_time = time.time()
                status_with_snapshot = session.query(BacktestStatus).join(StrategySnapshot).limit(100).all()
                join_query_time = time.time() - start_time
                
                logger.info(f"状态记录查询时间: {status_query_time:.4f}秒")
                logger.info(f"历史记录查询时间: {history_query_time:.4f}秒")
                logger.info(f"关联查询时间: {join_query_time:.4f}秒")
                
                # 性能阈值检查
                if status_query_time > 1.0 or history_query_time > 1.0 or join_query_time > 2.0:
                    logger.warning("查询性能可能存在问题")
                    return False
                
                logger.info("性能测试通过")
                return True
                
        except Exception as e:
            logger.error(f"性能测试失败: {str(e)}")
            return False
    
    def cleanup_test_data(self):
        """清理测试数据"""
        logger.info("清理测试数据...")
        
        try:
            with self.Session() as session:
                # 删除测试数据
                session.query(BacktestHistory).filter(
                    BacktestHistory.status_id.in_(
                        session.query(BacktestStatus.id).filter(
                            BacktestStatus.name.like("%测试回测%")
                        )
                    )
                ).delete(synchronize_session=False)
                
                session.query(BacktestStatus).filter(
                    BacktestStatus.name.like("%测试回测%")
                ).delete(synchronize_session=False)
                
                session.query(StrategySnapshot).filter(
                    StrategySnapshot.name == "测试策略"
                ).delete(synchronize_session=False)
                
                session.commit()
                logger.info("测试数据清理完成")
                
        except Exception as e:
            logger.error(f"清理测试数据失败: {str(e)}")
    
    def run_all_tests(self) -> Dict[str, bool]:
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("开始回测架构测试")
        logger.info("=" * 60)
        
        test_results = {}
        
        # 1. 测试创建状态记录
        test_results['create_status'] = self.test_create_status_record()
        
        # 2. 获取创建的状态记录ID
        status_id = None
        if test_results['create_status']:
            with self.Session() as session:
                status_record = session.query(BacktestStatus).filter(
                    BacktestStatus.name == "测试回测_001"
                ).first()
                if status_record:
                    status_id = status_record.id
        
        # 3. 测试创建历史记录
        if status_id:
            test_results['create_history'] = self.test_create_history_record(status_id)
        else:
            test_results['create_history'] = False
        
        # 4. 测试更新状态记录
        if status_id:
            test_results['update_status'] = self.test_update_status_record(status_id)
        else:
            test_results['update_status'] = False
        
        # 5. 测试查询操作
        test_results['query_operations'] = self.test_query_operations()
        
        # 6. 测试数据完整性
        test_results['data_integrity'] = self.test_data_integrity()
        
        # 7. 测试性能
        test_results['performance'] = self.test_performance()
        
        # 8. 清理测试数据
        self.cleanup_test_data()
        
        # 输出测试结果
        logger.info("=" * 60)
        logger.info("测试结果总结")
        logger.info("=" * 60)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "通过" if result else "失败"
            logger.info(f"{test_name}: {status}")
            if result:
                passed_tests += 1
        
        logger.info(f"总计: {passed_tests}/{total_tests} 个测试通过")
        
        if passed_tests == total_tests:
            logger.info("🎉 所有测试通过！新架构工作正常。")
        else:
            logger.warning("⚠️  部分测试失败，请检查相关功能。")
        
        return test_results

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='回测架构测试工具')
    parser.add_argument('--cleanup-only', action='store_true', help='仅清理测试数据')
    
    args = parser.parse_args()
    
    tester = BacktestArchitectureTester()
    
    try:
        if args.cleanup_only:
            tester.cleanup_test_data()
            return
        
        # 运行所有测试
        results = tester.run_all_tests()
        
        # 根据测试结果设置退出码
        if all(results.values()):
            sys.exit(0)  # 所有测试通过
        else:
            sys.exit(1)  # 有测试失败
            
    except Exception as e:
        logger.error(f"测试过程中发生严重错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
