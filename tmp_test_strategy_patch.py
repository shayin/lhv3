import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.models import get_db
from src.backend.api.strategy_routes import load_strategy_from_code
from src.backend.api.backtest_service import BacktestService

engine = create_engine('sqlite:////Users/shayin/data1/htdocs/project/joy/lhv3/backtesting.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

StrategyModel = __import__('src.backend.models.strategy', fromlist=['Strategy']).Strategy
strategy_row = session.query(StrategyModel).filter(StrategyModel.id==5).first()
code = strategy_row.code
print('原始 code 类型:', type(code))
if isinstance(code, (bytes, bytearray)):
    try:
        code = code.decode('utf-8')
    except:
        code = code.decode('latin-1')

patched = code.replace('for i in range(len(df)):', 'for i in range(len(prices)):')
if patched == code:
    print('没有找到要替换的字符串；尝试其他替换...')
else:
    print('已应用简单替换')

# 先用 BacktestService 获取数据
service = BacktestService(db=session)
stock_data = service.get_backtest_data('AAPL','2020-01-01','2023-12-31','database')
print('数据行数:', len(stock_data))

# 实例化修复后的策略
instance = load_strategy_from_code(patched, data=stock_data, parameters={'window_size':10,'min_change_pct':0.02,'min_distance':3,'max_extremums':30,'max_hold_days':10,'stop_loss':0.05,'take_profit':0.1,'max_position':0.3})
print('实例类型:', type(instance))

# 尝试生成信号
signals = instance.generate_signals()
print('signals shape:', signals.shape)
print(signals.head())
