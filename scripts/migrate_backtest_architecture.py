#!/usr/bin/env python3
"""
回测数据架构迁移脚本
将现有的 backtests 表数据迁移到新的 backtest_status 和 backtest_history 表架构
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.backend.models import get_engine, Backtest, BacktestStatus, BacktestHistory, StrategySnapshot
from src.backend.config import DATABASE_URL

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BacktestMigrator:
    """回测数据迁移器"""
    
    def __init__(self, db_url: str = None):
        """初始化迁移器"""
        self.db_url = db_url or DATABASE_URL
        self.engine = create_engine(self.db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        
    def analyze_existing_data(self) -> Dict[str, Any]:
        """分析现有数据"""
        logger.info("开始分析现有回测数据...")
        
        with self.Session() as session:
            # 统计现有数据
            total_backtests = session.query(Backtest).count()
            completed_backtests = session.query(Backtest).filter(Backtest.status == 'completed').count()
            
            # 按名称分组统计
            name_groups = session.execute(text("""
                SELECT name, COUNT(*) as count 
                FROM backtests 
                GROUP BY name 
                ORDER BY count DESC
            """)).fetchall()
            
            logger.info(f"总回测记录数: {total_backtests}")
            logger.info(f"已完成回测数: {completed_backtests}")
            logger.info(f"不同回测名称数: {len(name_groups)}")
            
            # 显示前10个最常见的回测名称
            logger.info("最常见的回测名称:")
            for name, count in name_groups[:10]:
                logger.info(f"  {name}: {count} 条记录")
            
            return {
                'total_backtests': total_backtests,
                'completed_backtests': completed_backtests,
                'name_groups': name_groups
            }
    
    def migrate_data(self, dry_run: bool = True) -> Dict[str, Any]:
        """迁移数据到新架构"""
        logger.info(f"开始迁移数据 (dry_run={dry_run})...")
        
        migration_stats = {
            'status_created': 0,
            'history_created': 0,
            'errors': []
        }
        
        with self.Session() as session:
            try:
                # 按回测名称分组，每个名称创建一个状态记录
                name_groups = session.execute(text("""
                    SELECT name, COUNT(*) as count 
                    FROM backtests 
                    GROUP BY name 
                    ORDER BY name
                """)).fetchall()
                
                for name, count in name_groups:
                    logger.info(f"处理回测名称: {name} ({count} 条记录)")
                    
                    # 获取该名称的所有回测记录，按创建时间排序
                    backtests = session.query(Backtest).filter(
                        Backtest.name == name
                    ).order_by(Backtest.created_at.asc()).all()
                    
                    if not backtests:
                        continue
                    
                    # 获取最新的回测记录作为状态记录
                    latest_backtest = backtests[-1]
                    
                    # 创建状态记录
                    if not dry_run:
                        status_record = BacktestStatus(
                            name=name,
                            description=latest_backtest.description,
                            strategy_id=latest_backtest.strategy_id,
                            strategy_snapshot_id=latest_backtest.strategy_snapshot_id,
                            start_date=latest_backtest.start_date,
                            end_date=latest_backtest.end_date,
                            initial_capital=latest_backtest.initial_capital,
                            instruments=latest_backtest.instruments,
                            parameters=latest_backtest.parameters,
                            position_config=latest_backtest.position_config,
                            results=latest_backtest.results,
                            equity_curve=latest_backtest.equity_curve,
                            trade_records=latest_backtest.trade_records,
                            performance_metrics=latest_backtest.performance_metrics,
                            status=latest_backtest.status,
                            created_at=latest_backtest.created_at,
                            completed_at=latest_backtest.completed_at
                        )
                        session.add(status_record)
                        session.flush()  # 获取ID
                        
                        migration_stats['status_created'] += 1
                        
                        # 为所有历史记录创建历史表记录
                        for i, backtest in enumerate(backtests):
                            operation_type = 'create' if i == 0 else 'update'
                            
                            history_record = BacktestHistory(
                                status_id=status_record.id,
                                start_date=backtest.start_date,
                                end_date=backtest.end_date,
                                initial_capital=backtest.initial_capital,
                                instruments=backtest.instruments,
                                parameters=backtest.parameters,
                                position_config=backtest.position_config,
                                results=backtest.results,
                                equity_curve=backtest.equity_curve,
                                trade_records=backtest.trade_records,
                                performance_metrics=backtest.performance_metrics,
                                status=backtest.status,
                                created_at=backtest.created_at,
                                completed_at=backtest.completed_at,
                                operation_type=operation_type
                            )
                            session.add(history_record)
                            migration_stats['history_created'] += 1
                    else:
                        # 模拟模式，只统计
                        migration_stats['status_created'] += 1
                        migration_stats['history_created'] += count
                
                if not dry_run:
                    session.commit()
                    logger.info("数据迁移完成!")
                else:
                    logger.info("模拟迁移完成!")
                    
            except Exception as e:
                logger.error(f"迁移过程中发生错误: {str(e)}")
                migration_stats['errors'].append(str(e))
                if not dry_run:
                    session.rollback()
        
        return migration_stats
    
    def verify_migration(self) -> Dict[str, Any]:
        """验证迁移结果"""
        logger.info("开始验证迁移结果...")
        
        verification_results = {
            'status_count': 0,
            'history_count': 0,
            'data_integrity_issues': []
        }
        
        with self.Session() as session:
            # 统计新表记录数
            verification_results['status_count'] = session.query(BacktestStatus).count()
            verification_results['history_count'] = session.query(BacktestHistory).count()
            
            # 检查数据完整性
            # 1. 检查是否有孤立的历史记录
            orphaned_history = session.execute(text("""
                SELECT COUNT(*) FROM backtest_history h
                LEFT JOIN backtest_status s ON h.status_id = s.id
                WHERE s.id IS NULL
            """)).scalar()
            
            if orphaned_history > 0:
                verification_results['data_integrity_issues'].append(
                    f"发现 {orphaned_history} 条孤立的历史记录"
                )
            
            # 2. 检查状态记录是否有对应的历史记录
            status_without_history = session.execute(text("""
                SELECT COUNT(*) FROM backtest_status s
                LEFT JOIN backtest_history h ON s.id = h.status_id
                WHERE h.id IS NULL
            """)).scalar()
            
            if status_without_history > 0:
                verification_results['data_integrity_issues'].append(
                    f"发现 {status_without_history} 个状态记录没有对应的历史记录"
                )
        
        logger.info(f"状态记录数: {verification_results['status_count']}")
        logger.info(f"历史记录数: {verification_results['history_count']}")
        
        if verification_results['data_integrity_issues']:
            logger.warning("发现数据完整性问题:")
            for issue in verification_results['data_integrity_issues']:
                logger.warning(f"  - {issue}")
        else:
            logger.info("数据完整性检查通过!")
        
        return verification_results
    
    def create_backup_tables(self):
        """创建备份表"""
        logger.info("创建备份表...")
        
        with self.engine.connect() as conn:
            # 备份原始表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS backtests_backup AS 
                SELECT * FROM backtests
            """))
            
            # 备份策略快照表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS strategy_snapshots_backup AS 
                SELECT * FROM strategy_snapshots
            """))
            
            conn.commit()
            logger.info("备份表创建完成!")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='回测数据架构迁移工具')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际修改数据')
    parser.add_argument('--analyze-only', action='store_true', help='仅分析现有数据')
    parser.add_argument('--verify-only', action='store_true', help='仅验证迁移结果')
    parser.add_argument('--create-backup', action='store_true', help='创建备份表')
    
    args = parser.parse_args()
    
    migrator = BacktestMigrator()
    
    try:
        if args.create_backup:
            migrator.create_backup_tables()
            return
        
        if args.analyze_only:
            migrator.analyze_existing_data()
            return
        
        if args.verify_only:
            migrator.verify_migration()
            return
        
        # 默认执行完整迁移流程
        logger.info("=" * 60)
        logger.info("回测数据架构迁移工具")
        logger.info("=" * 60)
        
        # 1. 分析现有数据
        analysis_results = migrator.analyze_existing_data()
        
        # 2. 创建备份
        if not args.dry_run:
            migrator.create_backup_tables()
        
        # 3. 执行迁移
        migration_results = migrator.migrate_data(dry_run=args.dry_run)
        
        # 4. 验证结果
        if not args.dry_run:
            verification_results = migrator.verify_migration()
        
        # 5. 输出总结
        logger.info("=" * 60)
        logger.info("迁移总结")
        logger.info("=" * 60)
        logger.info(f"原始回测记录数: {analysis_results['total_backtests']}")
        logger.info(f"创建状态记录数: {migration_results['status_created']}")
        logger.info(f"创建历史记录数: {migration_results['history_created']}")
        
        if migration_results['errors']:
            logger.error("迁移过程中的错误:")
            for error in migration_results['errors']:
                logger.error(f"  - {error}")
        
        if not args.dry_run:
            logger.info("迁移完成! 请验证数据完整性后删除备份表。")
        else:
            logger.info("模拟迁移完成! 使用 --dry-run=false 执行实际迁移。")
            
    except Exception as e:
        logger.error(f"迁移过程中发生严重错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
