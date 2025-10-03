from src.backend.api.backtest_service import BacktestService
from src.backend.models import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'backtesting.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

service = BacktestService(session)

result = service.run_backtest(
    strategy_id=6,
    symbol='AAPL',
    start_date='2022-09-30',
    end_date='2025-09-30',
    initial_capital=100000,
    commission_rate=0.0015,
    slippage_rate=0.001,
    parameters={
        'window_size': 10,
        'min_change_pct': 0.02,
        'min_distance': 3,
        'max_extremums': 30,
        'max_hold_days': 10,
        'stop_loss': 0.05,
        'take_profit': 0.1,
        'max_position': 0.3
    },
    data_source='database'
)

print('回测结果摘要:')
print(result.get('performance_metrics') if isinstance(result, dict) else result)
