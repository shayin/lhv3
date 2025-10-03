#!/usr/bin/env python3
"""
简短烟雾测试：验证回测引擎优先使用 signal['position_size'] 或策略建议仓位
输出断言结果并打印前几笔交易记录供人工检查。
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根到 sys.path
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.backend.api.strategy_routes import load_strategy_from_code
from src.backend.backtest.engine import BacktestEngine
from src.backend.api.backtest_service import BacktestService

# 数据库路径
DB_PATH = os.path.join(ROOT, 'backtesting.db')
engine_db = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine_db)
session = Session()
service = BacktestService(session)

# 读取数据（AAPL 范例区间）
df = service.get_backtest_data('AAPL','2022-09-30','2025-09-30',data_source='database')

# 读取策略代码
code_path = os.path.join(ROOT, 'src', 'backend', 'strategy', 'extremum_strategy_v5.py')
with open(code_path, 'r', encoding='utf-8') as f:
    code = f.read()

# 放宽参数以确保会产生交易
params = {'require_trend': False, 'signal_strength_threshold': 0.45, 'position_size_per_batch': 0.15, 'atr_sizing_factor': 0.1}

strategy = load_strategy_from_code(code, data=df, parameters=params)
strategy.set_data(df)

engine = BacktestEngine(strategy=strategy, initial_capital=100000, commission_rate=0.0015, slippage_rate=0.001)
result = engine.run(df)

trades = result.get('trades') or []
print('总交易笔数:', len(trades))

# 断言：存在至少两个买入交易且 position_size 在(0,1)之间
buy_trades = [t for t in trades if t.get('action') == 'BUY']
assert len(buy_trades) >= 2, '烟雾测试失败：买入交易不足'

violations = []
for t in buy_trades[:5]:
    ps = t.get('position_size')
    if ps is None:
        violations.append((t, 'missing position_size'))
    else:
        try:
            psf = float(ps)
            if not (0 < psf < 1):
                violations.append((t, f'position_size out of range: {psf}'))
        except Exception as e:
            violations.append((t, f'position_size not float: {e}'))

if violations:
    print('烟雾测试发现问题:')
    for v in violations:
        print(v)
    raise SystemExit(2)

print('烟雾测试通过：position_size 字段存在且在 (0,1) 之间（首5笔买入样本）')

# 打印首5笔交易供人工检查
for t in trades[:5]:
    print(t)

print('\n完成')
