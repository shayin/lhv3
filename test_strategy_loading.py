#!/usr/bin/env python3
"""
测试策略加载功能的独立脚本
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.models.strategy import Strategy as StrategyModel
from src.backend.config import DATABASE_URL

def test_strategy_loading():
    """测试策略加载功能"""
    
    # 创建数据库连接
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 获取策略ID为1的记录
        strategy = session.query(StrategyModel).filter(StrategyModel.id == 1).first()
        
        if not strategy:
            print("未找到策略ID为1的记录")
            return
            
        print(f"策略名称: {strategy.name}")
        print(f"策略代码长度: {len(strategy.code) if strategy.code else 0}")
        print("策略代码前300字符:")
        print(strategy.code[:300] if strategy.code else 'None')
        print("\n" + "="*50)
        
        # 尝试加载策略
        print("尝试加载策略...")
        
        # 导入必要的模块
        from src.backend.api.strategy_routes import load_strategy_from_code
        
        try:
            instance = load_strategy_from_code(strategy.code)
            print(f"策略加载成功: {type(instance)}")
            print(f"策略实例: {instance}")
            
            # 测试策略实例的基本方法
            if hasattr(instance, 'generate_signals'):
                print("策略实例具有generate_signals方法")
            else:
                print("警告: 策略实例缺少generate_signals方法")
                
        except Exception as e:
            print(f"策略加载失败: {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        session.close()

if __name__ == "__main__":
    test_strategy_loading()