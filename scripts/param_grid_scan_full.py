#!/usr/bin/env python3
"""
全面参数网格扫描（序列执行）
- 会尝试从 DB 中提取 v3/extremum 策略并备份
- 对比文件版 v5 与 DB 中的 v3（若存在）
- 将每组结果保存为 JSON，并生成 summary CSV
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

# 读取 v5 源码（文件）
v5_path = os.path.join(ROOT, 'src', 'backend', 'strategy', 'extremum_strategy_v5.py')
with open(v5_path, 'r', encoding='utf-8') as f:
    v5_code = f.read()

# 查找 DB 中的 v3/extremum 策略（尽量精确匹配 v3）
StrategyModel = __import__('src.backend.models.strategy', fromlist=['Strategy']).Strategy
candidate = session.query(StrategyModel).filter(StrategyModel.name.ilike('%v3%')).first()
if not candidate:
    candidate = session.query(StrategyModel).filter(StrategyModel.template.ilike('%extremum%')).first()

if candidate:
    db_name = candidate.name
    db_code = candidate.code
    if isinstance(db_code, (bytes, bytearray)):
        try:
            db_code = db_code.decode('utf-8')
        except Exception:
            db_code = db_code.decode('latin-1')
    # 备份到 data/backup
    backup_dir = os.path.join(ROOT, 'data', 'backup')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'strategy_db_backup_{db_name}_{now}.py')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(db_code)
    print('已备份 DB 策略到:', backup_path)
else:
    db_name = None
    db_code = None
    print('未找到 DB 中的 v3/extremum 策略，跳过 DB 对比')

# 测试证券与时间区间
symbol = 'AAPL'
start_date = '2022-09-30'
end_date = '2025-09-30'

data = service.get_backtest_data(symbol, start_date, end_date, data_source='database')

# 参数网格（扩大）
param_grid = {
    'require_trend': [True, False],
    'signal_strength_threshold': [0.65, 0.60, 0.55, 0.50, 0.45],
    'position_size_per_batch': [0.05, 0.08, 0.10, 0.12, 0.15],
    'max_hold_days': [10, 20, 30]
}

keys, values = zip(*param_grid.items())
combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
print(f'将运行 {len(combinations)} 组参数（顺序执行）')

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

    # 轻量进度输出
    if (i+1) % 10 == 0:
        print(f'已完成 {i+1}/{len(combinations)} 组')

# 保存 summary CSV
csv_path = os.path.join(out_dir, f'summary_full_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
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
