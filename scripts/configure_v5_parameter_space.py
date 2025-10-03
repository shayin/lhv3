#!/usr/bin/env python3
"""为 extremum_strategy_v5 在数据库中配置参数空间（备份后覆盖）。

用法: PYTHONPATH=./ python3 scripts/configure_v5_parameter_space.py
"""
import os
import json
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE, 'backtesting.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

# 导入模型
Strategy = __import__('src.backend.models.strategy', fromlist=['Strategy']).Strategy
ParameterSpace = __import__('src.backend.models.optimization', fromlist=['StrategyParameterSpace']).StrategyParameterSpace

# 查找 v5 策略
strategy = session.query(Strategy).filter(Strategy.template == 'extremum_v5').first()
if not strategy:
    strategy = session.query(Strategy).filter(Strategy.name == '极大极小值策略v5').first()

if not strategy:
    print('未找到 v5 策略，请先将 v5 插入数据库。')
    exit(1)

sid = strategy.id
now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup_dir = os.path.join(BASE, 'data', 'backup')
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

# 备份现有 v5 的 parameter spaces
existing = session.query(ParameterSpace).filter(ParameterSpace.strategy_id == sid).all()
backup_path = os.path.join(backup_dir, f'parameter_spaces_v5_backup_{now}.json')
existing_data = []
for e in existing:
    existing_data.append({
        'id': e.id,
        'parameter_name': e.parameter_name,
        'parameter_type': e.parameter_type,
        'min_value': e.min_value,
        'max_value': e.max_value,
        'step_size': e.step_size,
        'choices': e.choices,
        'description': e.description,
        'created_at': e.created_at.isoformat() if e.created_at else None,
    })
with open(backup_path, 'w', encoding='utf-8') as f:
    json.dump(existing_data, f, ensure_ascii=False, indent=2)
print('Backed up existing parameter spaces for v5 to', backup_path)

# 删除旧条目
if existing:
    for e in existing:
        session.delete(e)
    session.commit()
    print('Deleted existing parameter spaces for v5')

# 定义新的参数空间
param_spaces = [
    # lookback_period: 5-40 step 5
    {'parameter_name': 'lookback_period', 'parameter_type': 'int', 'min_value': 5, 'max_value': 40, 'step_size': 5, 'choices': None, 'description': '极值识别的回溯窗口'},
    {'parameter_name': 'min_price_change', 'parameter_type': 'float', 'min_value': 0.01, 'max_value': 0.20, 'step_size': 0.01, 'choices': None, 'description': '识别极值时的最小价格变化比例'},
    {'parameter_name': 'max_extremums', 'parameter_type': 'int', 'min_value': 10, 'max_value': 200, 'step_size': 10, 'choices': None, 'description': '最大保存的极值点数量'},
    {'parameter_name': 'min_extremum_distance', 'parameter_type': 'int', 'min_value': 1, 'max_value': 20, 'step_size': 1, 'choices': None, 'description': '极值点之间的最小距离（天）'},

    # batch
    {'parameter_name': 'batch_count', 'parameter_type': 'int', 'min_value': 1, 'max_value': 8, 'step_size': 1, 'choices': None, 'description': '分批建仓的批次数'},
    {'parameter_name': 'batch_interval', 'parameter_type': 'int', 'min_value': 1, 'max_value': 10, 'step_size': 1, 'choices': None, 'description': '分批建仓的间隔（天）'},
    {'parameter_name': 'position_size_per_batch', 'parameter_type': 'float', 'min_value': 0.05, 'max_value': 0.5, 'step_size': 0.05, 'choices': None, 'description': '每批建仓占总仓位比例'},

    # 风险止损
    {'parameter_name': 'stop_loss_ratio', 'parameter_type': 'float', 'min_value': 0.01, 'max_value': 0.20, 'step_size': 0.01, 'choices': None, 'description': '初始止损比例'},
    {'parameter_name': 'trailing_stop_pct', 'parameter_type': 'float', 'min_value': 0.01, 'max_value': 0.20, 'step_size': 0.01, 'choices': None, 'description': '移动止损百分比'},
    {'parameter_name': 'take_profit_ratio', 'parameter_type': 'float', 'min_value': 0.05, 'max_value': 0.5, 'step_size': 0.05, 'choices': None, 'description': '止盈比例'},
    {'parameter_name': 'max_position_ratio', 'parameter_type': 'float', 'min_value': 0.1, 'max_value': 1.0, 'step_size': 0.1, 'choices': None, 'description': '最大持仓比例'},

    # 趋势过滤
    {'parameter_name': 'trend_ma_long', 'parameter_type': 'int', 'min_value': 20, 'max_value': 200, 'step_size': 10, 'choices': None, 'description': '长期趋势均线周期'},
    {'parameter_name': 'require_trend', 'parameter_type': 'choice', 'min_value': None, 'max_value': None, 'step_size': None, 'choices': [True, False], 'description': '是否启用趋势过滤'},

    # ATR
    {'parameter_name': 'atr_period', 'parameter_type': 'int', 'min_value': 5, 'max_value': 30, 'step_size': 1, 'choices': None, 'description': 'ATR 计算周期'},
    {'parameter_name': 'atr_sizing_factor', 'parameter_type': 'float', 'min_value': 0.1, 'max_value': 2.0, 'step_size': 0.1, 'choices': None, 'description': 'ATR 自适应仓位乘子'},

    # 信号
    {'parameter_name': 'signal_strength_threshold', 'parameter_type': 'float', 'min_value': 0.3, 'max_value': 0.9, 'step_size': 0.05, 'choices': None, 'description': '信号强度阈值'},
    {'parameter_name': 'max_hold_days', 'parameter_type': 'int', 'min_value': 5, 'max_value': 60, 'step_size': 5, 'choices': None, 'description': '最大持仓天数'},
]

# 插入新参数空间
inserted = []
for p in param_spaces:
    ps = ParameterSpace(
        strategy_id=sid,
        parameter_name=p['parameter_name'],
        parameter_type=p['parameter_type'],
        min_value=p['min_value'],
        max_value=p['max_value'],
        step_size=p['step_size'],
        choices=p['choices'],
        description=p['description']
    )
    session.add(ps)
    inserted.append(p['parameter_name'])

session.commit()
print('Inserted parameter spaces:', inserted)

# 列出刚插入的条目
rows = session.query(ParameterSpace).filter(ParameterSpace.strategy_id == sid).all()
for r in rows:
    print(f"- {r.parameter_name}: type={r.parameter_type}, min={r.min_value}, max={r.max_value}, step={r.step_size}, choices={r.choices}")

print('Done')
