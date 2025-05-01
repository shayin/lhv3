import sys
import os
import json
import requests
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.models.base import init_db
from backend.models.strategy import Strategy

def test_create_strategy():
    """测试创建策略API"""
    print("初始化数据库...")
    init_db()
    
    print("\n开始测试创建策略API...")
    
    # 准备测试数据
    strategy_data = {
        "name": "测试移动平均线策略",
        "description": "基于短期和长期移动平均线交叉产生交易信号的策略",
        "parameters": {
            "symbol": "000300.SH",
            "timeframe": "D",
            "shortPeriod": 20,
            "longPeriod": 60,
            "positionSizing": "all_in"
        }
    }
    
    # 直接使用SQLAlchemy模型创建记录
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.config import DATABASE_URL
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 创建策略记录
        strategy = Strategy(
            name=strategy_data["name"],
            description=strategy_data["description"],
            parameters=strategy_data["parameters"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_template=False
        )
        
        session.add(strategy)
        session.commit()
        
        # 查询刚创建的策略
        created_strategy = session.query(Strategy).filter_by(name=strategy_data["name"]).first()
        
        if created_strategy:
            print(f"策略创建成功! ID: {created_strategy.id}")
            print(f"策略名称: {created_strategy.name}")
            print(f"策略描述: {created_strategy.description}")
            print(f"策略参数: {created_strategy.parameters}")
            print(f"创建时间: {created_strategy.created_at}")
        else:
            print("策略创建失败!")
            
    except Exception as e:
        print(f"测试失败: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_create_strategy() 