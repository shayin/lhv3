#!/usr/bin/env python3
"""覆盖数据库中 v5 策略的 code 字段（安全流程：先备份 strategies 表到 JSON）。"""
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
StrategyModel = __import__('src.backend.models.strategy', fromlist=['Strategy']).Strategy

now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup_dir = os.path.join(BASE, 'data', 'backup')
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

# 1) 备份 strategies 表到 JSON
strategies = session.query(StrategyModel).all()
strategies_data = []
for s in strategies:
    strategies_data.append({
        'id': s.id,
        'name': s.name,
        'template': s.template,
        'is_template': bool(s.is_template),
        'description': s.description,
        'parameters': s.parameters,
    })
backup_path = os.path.join(backup_dir, f'strategies_backup_{now}.json')
with open(backup_path, 'w', encoding='utf-8') as f:
    json.dump(strategies_data, f, ensure_ascii=False, indent=2)
print('Backed up strategies to', backup_path)

# 2) 读取 v5 源码
strategy_file = os.path.join(BASE, 'src', 'backend', 'strategy', 'extremum_strategy_v5.py')
with open(strategy_file, 'r', encoding='utf-8') as f:
    code = f.read()

# 3) 查找目标记录（优先使用 template 字段，其次使用 name）
target = session.query(StrategyModel).filter(StrategyModel.template == 'extremum_v5').first()
if not target:
    target = session.query(StrategyModel).filter(StrategyModel.name == '极大极小值策略v5').first()

if not target:
    # 如果没有则插入
    s = StrategyModel(
        name='极大极小值策略v5',
        description='基于 v2 的改进版，增加趋势过滤、ATR 自适应仓位与移动止损',
        code=code,
        parameters=None,
        template='extremum_v5',
        is_template=True
    )
    session.add(s)
    session.flush()
    session.commit()
    print('Inserted new v5, ID:', s.id)
else:
    # 覆盖 code
    print('Updating existing strategy ID:', target.id)
    target.code = code
    try:
        session.commit()
        print('Updated strategy ID:', target.id)
    except Exception as e:
        session.rollback()
        print('Failed to update strategy:', e)

print('Done')
