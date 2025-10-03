import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.api.strategy_routes import load_strategy_from_code
from src.backend.models import get_db

# 直接使用应用的 SQLite 数据库
engine = create_engine('sqlite:////Users/shayin/data1/htdocs/project/joy/lhv3/backtesting.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

StrategyModel = __import__('src.backend.models.strategy', fromlist=['Strategy']).Strategy

strategy = session.query(StrategyModel).filter(StrategyModel.id==5).first()
print('策略名称:', strategy.name)
try:
    instance = load_strategy_from_code(strategy.code, data=None, parameters=None)
    print('实例化成功', type(instance))
except Exception as e:
    import traceback
    traceback.print_exc()
    print('错误:', e)
