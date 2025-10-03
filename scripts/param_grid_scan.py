#!/usr/bin/env python3
"""
参数网格扫描脚本（精简版）
- 对比两个策略：源码文件（extremum_strategy_v5.py）与 数据库中同名策略（若存在）
- 对每组参数运行回测并保存结果到 data/scan_results/{timestamp}_{strategy_name}.json 和 CSV 汇总

注意：这是一个精简的扫描实现；可选并行执行（稍后扩展）。
"""
import os
import json
import itertools
import datetime
import csv

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in __import__('sys').path:
    __import__('sys').path.insert(0, ROOT)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.api.strategy_routes import load_strategy_from_code
from src.backend.api.backtest_service import BacktestService
from src.backend.backtest.engine import BacktestEngine

# DB
DB_PATH = os.path.join(ROOT, 'backtesting.db')
engine_db = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine_db)
session = Session()
service = BacktestService(session)

# 输出目录
out_dir = os.path.join(ROOT, 'data', 'scan_results')
if not os.path.exists(out_dir):
    os.makedirs(out_dir)

# 策略一: 文件版 v5
v5_path = os.path.join(ROOT, 'src', 'backend', 'strategy', 'extremum_strategy_v5.py')
with open(v5_path, 'r', encoding='utf-8') as f:
    v5_code = f.read()

# 策略二: 从 DB 读取（尝试查找 extremum 或 v3）
StrategyModel = __import__('src.backend.models.strategy', fromlist=['Strategy']).Strategy
candidate = session.query(StrategyModel).filter(StrategyModel.template.ilike('%extremum%')).first()
if candidate:
    db_name = candidate.name
    db_code = candidate.code
    if isinstance(db_code, (bytes, bytearray)):
        try:
            db_code = db_code.decode('utf-8')
        except Exception:
            db_code = db_code.decode('latin-1')
    print('找到数据库策略:', db_name)
else:
    db_code = None
    db_name = None
    print('数据库中未找到 extremum 类策略，跳过 DB 对比')

# 测试证券与时间区间
symbol = 'AAPL'
start_date = '2022-09-30'
end_date = '2025-09-30'

data = service.get_backtest_data(symbol, start_date, end_date, data_source='database')

# 参数网格（示例，小规模）
param_grid = {
    'require_trend': [True, False],
    'signal_strength_threshold': [0.55, 0.45],
    'position_size_per_batch': [0.10, 0.15]
}

keys, values = zip(*param_grid.items())
combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
print(f'将运行 {len(combinations)} 组参数')

summary_rows = []

for i, params in enumerate(combinations):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    # v5 文件版
    strategy = load_strategy_from_code(v5_code, data=data, parameters=params)
    strategy.set_data(data)
    engine = BacktestEngine(strategy=strategy, initial_capital=100000, commission_rate=0.0015, slippage_rate=0.001)
    result_v5 = engine.run(data)
    out_path_v5 = os.path.join(out_dir, f'{stamp}_v5_{i}.json')
    with open(out_path_v5, 'w', encoding='utf-8') as f:
        json.dump({'params': params, 'result': result_v5}, f, default=str, indent=2)

    summary_rows.append({'strategy': 'v5_file', 'idx': i, 'params': params, 'total_return': result_v5.get('total_return'), 'max_drawdown': result_v5.get('max_drawdown'), 'trades': len(result_v5.get('trades') or [])})

    # 如果存在 DB 策略则运行对比
    if db_code:
        strategy_db = load_strategy_from_code(db_code, data=data, parameters=params)
        strategy_db.set_data(data)
        engine_db = BacktestEngine(strategy=strategy_db, initial_capital=100000, commission_rate=0.0015, slippage_rate=0.001)
        result_db = engine_db.run(data)
        out_path_db = os.path.join(out_dir, f'{stamp}_db_{i}.json')
        with open(out_path_db, 'w', encoding='utf-8') as f:
            json.dump({'params': params, 'result': result_db}, f, default=str, indent=2)
        summary_rows.append({'strategy': f'db_{db_name}', 'idx': i, 'params': params, 'total_return': result_db.get('total_return'), 'max_drawdown': result_db.get('max_drawdown'), 'trades': len(result_db.get('trades') or [])})

# 保存 summary CSV
csv_path = os.path.join(out_dir, f'summary_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['strategy', 'idx', 'params', 'total_return', 'max_drawdown', 'trades']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for r in summary_rows:
        r2 = r.copy()
        r2['params'] = json.dumps(r2['params'], ensure_ascii=False)
        writer.writerow(r2)

print('扫描完成，结果保存在:', out_dir)
print('summary:', csv_path)
