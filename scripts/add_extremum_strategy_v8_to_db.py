#!/usr/bin/env python3
"""将极大极小值策略v8添加到数据库中"""
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

# 2) 读取极大极小值策略v8源码
strategy_file = os.path.join(BASE, 'src', 'backend', 'strategy', 'extremum_strategy_v8.py')
with open(strategy_file, 'r', encoding='utf-8') as f:
    code = f.read()

# 3) 查找是否已存在该策略（优先使用 template 字段，其次使用 name）
target = session.query(StrategyModel).filter(StrategyModel.template == 'extremum_v8').first()
if not target:
    target = session.query(StrategyModel).filter(StrategyModel.name == '极大极小值策略v8').first()

# 4) 默认参数配置
default_parameters = json.dumps({
    # 极值识别基础参数
    "lookback_period": 12,
    "min_price_change_pct": 0.03,
    "extremum_confirm_days": 3,
    
    # 均线参数
    "ma_short": 10,
    "ma_long": 20,
    "ma_cross_confirm": True,
    
    # 趋势转折识别参数
    "trend_reversal_points": 5,
    "reversal_threshold_pct": 0.02,
    
    # RSI参数
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "rsi_confirm": True,
    
    # 成交量确认参数
    "volume_ma_period": 20,
    "volume_amplify_ratio": 1.5,
    "volume_confirm": True,
    
    # 信号强度参数
    "signal_strength_threshold": 0.65,
    "max_signals_per_period": 3,
    
    # 仓位管理参数 - V8修正版
    "base_position_size": 0.05,
    "max_position_ratio": 0.8,
    "position_scaling": True,
    
    # 风险控制参数
    "stop_loss_pct": 0.06,
    "take_profit_pct": 0.15,
    "trailing_stop_pct": 0.04,
    "max_hold_days": 25,
    
    # 市场环境过滤
    "market_trend_period": 50,
    "bear_market_threshold": -0.1,
    "bull_market_threshold": 0.1
}, ensure_ascii=False)

if not target:
    # 创建新策略
    print('Creating new extremum strategy v8...')
    s = StrategyModel(
        name='极大极小值策略v8',
        description='极大极小值策略v8 - 修正仓位管理版本。基于V6策略，主要改进：统一买入和卖出的仓位计算方式，确保买入和卖出的仓位大小一致，避免卖出过少的问题。',
        code=code,
        parameters=default_parameters,
        template='extremum_v8',
        is_template=True
    )
    session.add(s)
    session.flush()
    session.commit()
    print('Inserted new extremum strategy v8, ID:', s.id)
else:
    # 更新现有策略
    print('Updating existing extremum strategy v8 ID:', target.id)
    target.code = code
    target.description = '极大极小值策略v8 - 修正仓位管理版本。基于V6策略，主要改进：统一买入和卖出的仓位计算方式，确保买入和卖出的仓位大小一致，避免卖出过少的问题。'
    target.parameters = default_parameters
    target.updated_at = datetime.datetime.now()
    try:
        session.commit()
        print('Updated extremum strategy v8 ID:', target.id)
    except Exception as e:
        session.rollback()
        print('Failed to update strategy:', e)

session.close()
print('Done')