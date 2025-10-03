from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from src.backend.api.backtest_service import BacktestService
from src.backend.api.strategy_routes import load_strategy_from_code

DB_PATH = os.path.join(os.path.dirname(__file__), 'backtesting.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

service = BacktestService(session)

# 获取数据
start='2022-09-30'
end='2025-09-30'
df = service.get_backtest_data('AAPL', start, end, data_source='database')
print('数据行数:', len(df))

# 读取 v5 源码并实例化
code = open('src/backend/strategy/extremum_strategy_v5.py','r',encoding='utf-8').read()
strategy = load_strategy_from_code(code, data=df, parameters={})
strategy.set_data(df)

prices = df['close']

found = 0
for i in range(len(df)):
    mins, maxs = strategy.find_extremums_rolling(prices, i)
    if hasattr(mins, '__len__') and len(mins) > 0:
        found += 1
        print('i=', i, 'date=', df.iloc[i]['date'], 'mins_count=', len(mins), 'maxs_count=', len(maxs), 'mins_sample=', mins[:5], 'maxs_sample=', maxs[:5])
        if found >= 10:
            break

print('共发现非空极小极大索引的时间点数量(前10展示):', found)
