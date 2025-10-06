#!/usr/bin/env python3
"""
数据库索引优化脚本
为关键表创建性能优化索引，提升查询性能
"""

import sys
import os
import sqlite3
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'src', 'backend'))

def create_database_indexes():
    """创建数据库索引"""
    db_path = os.path.join(project_root, 'backtesting.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("开始创建数据库索引...")
        
        # 1. 股票数据表索引
        indexes_to_create = [
            # stock_data表索引 - 提升按股票和日期查询的性能
            ("idx_stock_data_stock_date", "CREATE INDEX IF NOT EXISTS idx_stock_data_stock_date ON stock_data(stock_id, date)"),
            ("idx_stock_data_date", "CREATE INDEX IF NOT EXISTS idx_stock_data_date ON stock_data(date)"),
            ("idx_stock_data_close", "CREATE INDEX IF NOT EXISTS idx_stock_data_close ON stock_data(close)"),
            
            # stocks表索引 - 提升股票查询性能
            ("idx_stocks_symbol", "CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stocks(symbol)"),
            ("idx_stocks_type", "CREATE INDEX IF NOT EXISTS idx_stocks_type ON stocks(type)"),
            ("idx_stocks_last_updated", "CREATE INDEX IF NOT EXISTS idx_stocks_last_updated ON stocks(last_updated)"),
            
            # strategies表索引 - 提升策略查询性能
            ("idx_strategies_name", "CREATE INDEX IF NOT EXISTS idx_strategies_name ON strategies(name)"),
            ("idx_strategies_template", "CREATE INDEX IF NOT EXISTS idx_strategies_template ON strategies(template)"),
            ("idx_strategies_created_at", "CREATE INDEX IF NOT EXISTS idx_strategies_created_at ON strategies(created_at)"),
            
            # backtests表索引 - 提升回测查询性能
            ("idx_backtests_strategy_id", "CREATE INDEX IF NOT EXISTS idx_backtests_strategy_id ON backtests(strategy_id)"),
            ("idx_backtests_status", "CREATE INDEX IF NOT EXISTS idx_backtests_status ON backtests(status)"),
            ("idx_backtests_created_at", "CREATE INDEX IF NOT EXISTS idx_backtests_created_at ON backtests(created_at)"),
            ("idx_backtests_start_date", "CREATE INDEX IF NOT EXISTS idx_backtests_start_date ON backtests(start_date)"),
            
            # backtest_status表索引 - 提升回测状态查询性能
            ("idx_backtest_status_name", "CREATE INDEX IF NOT EXISTS idx_backtest_status_name ON backtest_status(name)"),
            ("idx_backtest_status_updated_at", "CREATE INDEX IF NOT EXISTS idx_backtest_status_updated_at ON backtest_status(updated_at)"),
            ("idx_backtest_status_status", "CREATE INDEX IF NOT EXISTS idx_backtest_status_status ON backtest_status(status)"),
            ("idx_backtest_status_strategy_id", "CREATE INDEX IF NOT EXISTS idx_backtest_status_strategy_id ON backtest_status(strategy_id)"),
            
            # backtest_history表索引 - 提升历史记录查询性能
            ("idx_backtest_history_status_id", "CREATE INDEX IF NOT EXISTS idx_backtest_history_status_id ON backtest_history(status_id)"),
            ("idx_backtest_history_created_at", "CREATE INDEX IF NOT EXISTS idx_backtest_history_created_at ON backtest_history(created_at)"),
            ("idx_backtest_history_operation_type", "CREATE INDEX IF NOT EXISTS idx_backtest_history_operation_type ON backtest_history(operation_type)"),
            
            # trades表索引 - 提升交易记录查询性能
            ("idx_trades_backtest_date", "CREATE INDEX IF NOT EXISTS idx_trades_backtest_date ON trades(backtest_id, datetime)"),
            ("idx_trades_symbol", "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)"),
            ("idx_trades_datetime", "CREATE INDEX IF NOT EXISTS idx_trades_datetime ON trades(datetime)"),
            
            # optimization相关表索引
            ("idx_optimization_jobs_strategy_id", "CREATE INDEX IF NOT EXISTS idx_optimization_jobs_strategy_id ON optimization_jobs(strategy_id)"),
            ("idx_optimization_jobs_status", "CREATE INDEX IF NOT EXISTS idx_optimization_jobs_status ON optimization_jobs(status)"),
            ("idx_optimization_jobs_created_at", "CREATE INDEX IF NOT EXISTS idx_optimization_jobs_created_at ON optimization_jobs(created_at)"),
            
            ("idx_optimization_trials_job_id", "CREATE INDEX IF NOT EXISTS idx_optimization_trials_job_id ON optimization_trials(job_id)"),
            ("idx_optimization_trials_status", "CREATE INDEX IF NOT EXISTS idx_optimization_trials_status ON optimization_trials(status)"),
            ("idx_optimization_trials_objective_value", "CREATE INDEX IF NOT EXISTS idx_optimization_trials_objective_value ON optimization_trials(objective_value)"),
            
            # technical_indicators表索引
            ("idx_technical_indicators_stock_date", "CREATE INDEX IF NOT EXISTS idx_technical_indicators_stock_date ON technical_indicators(stock_id, date)"),
            ("idx_technical_indicators_name", "CREATE INDEX IF NOT EXISTS idx_technical_indicators_name ON technical_indicators(indicator_name)"),
        ]
        
        created_count = 0
        for index_name, sql in indexes_to_create:
            try:
                cursor.execute(sql)
                print(f"✅ 创建索引: {index_name}")
                created_count += 1
            except sqlite3.Error as e:
                if "already exists" in str(e).lower():
                    print(f"⚠️  索引已存在: {index_name}")
                else:
                    print(f"❌ 创建索引失败 {index_name}: {e}")
        
        # 提交更改
        conn.commit()
        
        print(f"\n索引创建完成！成功创建 {created_count} 个索引")
        
        # 分析数据库以更新统计信息
        print("\n正在分析数据库以更新统计信息...")
        cursor.execute("ANALYZE")
        conn.commit()
        print("✅ 数据库分析完成")
        
        return True
        
    except Exception as e:
        print(f"创建索引时发生错误: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def show_existing_indexes():
    """显示现有索引"""
    db_path = os.path.join(project_root, 'backtesting.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("现有索引列表:")
        print("-" * 60)
        
        cursor.execute("""
            SELECT name, sql 
            FROM sqlite_master 
            WHERE type = 'index' 
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        indexes = cursor.fetchall()
        for name, sql in indexes:
            print(f"索引名: {name}")
            if sql:
                print(f"SQL: {sql}")
            print("-" * 60)
        
        print(f"\n总计: {len(indexes)} 个索引")
        
    except Exception as e:
        print(f"查询索引时发生错误: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def check_query_performance():
    """检查查询性能"""
    db_path = os.path.join(project_root, 'backtesting.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("查询性能测试:")
        print("-" * 60)
        
        # 测试查询
        test_queries = [
            ("股票数据按日期查询", "SELECT COUNT(*) FROM stock_data WHERE date >= '2023-01-01'"),
            ("回测状态查询", "SELECT COUNT(*) FROM backtest_status WHERE status = 'completed'"),
            ("策略查询", "SELECT COUNT(*) FROM strategies WHERE template = 'extremum_v7'"),
            ("交易记录查询", "SELECT COUNT(*) FROM trades WHERE datetime >= '2023-01-01'"),
        ]
        
        import time
        for desc, query in test_queries:
            start_time = time.time()
            cursor.execute(query)
            result = cursor.fetchone()[0]
            end_time = time.time()
            
            print(f"{desc}: {result} 条记录, 耗时: {(end_time - start_time)*1000:.2f}ms")
        
    except Exception as e:
        print(f"性能测试时发生错误: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库索引管理工具")
    parser.add_argument("--create", action="store_true", help="创建索引")
    parser.add_argument("--show", action="store_true", help="显示现有索引")
    parser.add_argument("--test", action="store_true", help="测试查询性能")
    
    args = parser.parse_args()
    
    if args.show:
        show_existing_indexes()
    
    if args.create:
        create_database_indexes()
    
    if args.test:
        check_query_performance()
    
    if not any([args.create, args.show, args.test]):
        print("使用方法:")
        print("  python create_database_indexes.py --create  # 创建索引")
        print("  python create_database_indexes.py --show    # 显示现有索引")
        print("  python create_database_indexes.py --test    # 测试查询性能")
        print("  python create_database_indexes.py --create --test  # 创建索引并测试性能")