from src.backend.api.strategy_routes import load_strategy_from_code
from src.backend.api.backtest_service import BacktestService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'backtesting.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)
session = Session()
service = BacktestService(session)

df = service.get_backtest_data('AAPL', '2022-09-30', '2025-09-30', data_source='database')
print('data rows', len(df))

code = open('src/backend/strategy/extremum_strategy_v5.py','r',encoding='utf-8').read()
params = {'require_trend': False, 'signal_strength_threshold': 0.45, 'position_size_per_batch': 0.15, 'atr_sizing_factor': 0.1}
strategy = load_strategy_from_code(code, data=df, parameters=params)
strategy.set_data(df)

prices = df['close']

print('Checking candidates...')
count=0
for i in range(len(df)):
    mins, maxs = strategy.find_extremums_rolling(prices, i)
    if hasattr(mins, '__len__') and len(mins)>0:
        for extremum_idx in mins:
            strength = strategy.calculate_signal_strength_optimized(i, extremum_idx, prices, df)
            batch = strategy.adaptive_batch_size(i, df)
            threshold = strategy.parameters.get('signal_strength_threshold',0.6)
            if strength > threshold:
                print('i',i,'date',df.iloc[i]['date'],'extremum',extremum_idx,'strength',strength,'threshold',threshold,'batch',batch)
                count+=1
                if count>=30:
                    break
    if count>=30:
        break

print('found',count)
