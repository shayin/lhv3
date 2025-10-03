import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.api.backtest_service import BacktestService

engine = create_engine('sqlite:////Users/shayin/data1/htdocs/project/joy/lhv3/backtesting.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

service = BacktestService(db=session)

result = service.run_backtest(
    strategy_id=5,
    symbol='AAPL',
    start_date='2020-01-01',
    end_date='2023-12-31',
    initial_capital=100000,
    commission_rate=0.0015,
    slippage_rate=0.001,
    data_source='database',
    parameters={
        'positionConfig': {'mode': 'staged', 'sizes': [0.25,0.25,0.25,0.25], 'defaultSize': 1},
        'save_backtest': False,
        'parameters': {
            'window_size': 10,
            'min_change_pct': 0.02,
            'min_distance': 3,
            'max_extremums': 30,
            'max_hold_days': 10,
            'stop_loss': 0.05,
            'take_profit': 0.1,
            'max_position': 0.3
        }
    }
)

print(json.dumps(result, indent=2, ensure_ascii=False))
