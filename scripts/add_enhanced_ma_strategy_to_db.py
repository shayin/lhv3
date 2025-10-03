#!/usr/bin/env python3
"""将增强型移动平均策略添加到数据库中"""
import os
import sys
import json
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE = os.path.dirname(os.path.dirname(__file__))
# 添加项目根目录到Python路径
sys.path.insert(0, BASE)

DB_PATH = os.path.join(BASE, 'backtesting.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

# 导入模型
from src.backend.models.strategy import Strategy as StrategyModel

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

# 2) 读取增强型移动平均策略源码
strategy_file = os.path.join(BASE, 'src', 'backend', 'strategy', 'enhanced_ma_strategy.py')
with open(strategy_file, 'r', encoding='utf-8') as f:
    code = f.read()

# 3) 查找是否已存在该策略（优先使用 template 字段，其次使用 name）
target = session.query(StrategyModel).filter(StrategyModel.template == 'enhanced_ma').first()
if not target:
    target = session.query(StrategyModel).filter(StrategyModel.name == '增强型移动平均策略').first()

# 4) 默认参数配置
default_parameters = json.dumps({
    "short_window": 5,
    "long_window": 20,
    "max_total_position": 1.0,
    "stage1_position": 0.3,
    "stage2_position": 0.7,
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "volume_threshold": 1.2,
    "stop_loss": 0.05,
    "take_profit": 0.15
}, ensure_ascii=False)

if not target:
    # 创建新策略
    print('Creating new enhanced MA strategy...')
    s = StrategyModel(
        name='增强型移动平均策略',
        description='基于移动平均线的增强型策略，支持分阶段建仓、RSI过滤、成交量确认和止盈止损',
        code=code,
        parameters=default_parameters,
        template='enhanced_ma',
        is_template=True
    )
    session.add(s)
    session.flush()
    session.commit()
    print('Inserted new enhanced MA strategy, ID:', s.id)
else:
    # 更新现有策略
    print('Updating existing enhanced MA strategy ID:', target.id)
    target.code = code
    target.description = '基于移动平均线的增强型策略，支持分阶段建仓、RSI过滤、成交量确认和止盈止损'
    target.parameters = default_parameters
    target.updated_at = datetime.datetime.now()
    try:
        session.commit()
        print('Updated enhanced MA strategy ID:', target.id)
    except Exception as e:
        session.rollback()
        print('Failed to update strategy:', e)

session.close()
print('Done')