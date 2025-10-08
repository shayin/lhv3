#!/usr/bin/env python3
"""
测试回测服务中的策略实例创建功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.models.strategy import Strategy as StrategyModel
from src.backend.config import DATABASE_URL
from src.backend.api.backtest_service import BacktestService

def test_backtest_service():
    """测试回测服务中的策略实例创建"""
    
    # 创建数据库连接
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 创建回测服务实例
        backtest_service = BacktestService(db=session)
        
        # 获取策略ID为1的记录
        strategy = session.query(StrategyModel).filter(StrategyModel.id == 1).first()
        
        if not strategy:
            print("未找到策略ID为1的记录")
            return
            
        print(f"策略名称: {strategy.name}")
        print(f"策略ID: {strategy.id}")
        
        # 创建一些测试数据
        test_data = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=10),
            'open': [100 + i for i in range(10)],
            'high': [105 + i for i in range(10)],
            'low': [95 + i for i in range(10)],
            'close': [102 + i for i in range(10)],
            'volume': [1000 + i*100 for i in range(10)]
        })
        
        print(f"测试数据形状: {test_data.shape}")
        print("测试数据前5行:")
        print(test_data.head())
        
        # 测试策略实例创建
        print("\n" + "="*50)
        print("测试策略实例创建...")
        
        # 测试不同的参数组合
        test_cases = [
            {"case": "无参数", "strategy_id": 1, "data": None, "parameters": None},
            {"case": "有数据无参数", "strategy_id": 1, "data": test_data, "parameters": None},
            {"case": "有数据有参数", "strategy_id": 1, "data": test_data, "parameters": {"ma_short": 5, "ma_long": 20}},
            {"case": "字符串ID", "strategy_id": "1", "data": test_data, "parameters": {"ma_short": 5, "ma_long": 20}},
        ]
        
        for test_case in test_cases:
            print(f"\n测试案例: {test_case['case']}")
            try:
                instance = backtest_service._get_strategy_instance(
                    strategy_id=test_case['strategy_id'],
                    data=test_case['data'],
                    parameters=test_case['parameters']
                )
                
                if instance:
                    print(f"  ✓ 策略实例创建成功: {type(instance)}")
                    print(f"  ✓ 策略实例: {instance}")
                    
                    # 测试策略实例的基本方法
                    if hasattr(instance, 'generate_signals'):
                        print("  ✓ 策略实例具有generate_signals方法")
                    else:
                        print("  ⚠ 警告: 策略实例缺少generate_signals方法")
                else:
                    print(f"  ✗ 策略实例创建失败: 返回None")
                    
            except Exception as e:
                print(f"  ✗ 策略实例创建异常: {e}")
                import traceback
                traceback.print_exc()
                
    finally:
        session.close()

if __name__ == "__main__":
    test_backtest_service()