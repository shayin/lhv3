#!/usr/bin/env python3
"""将极大极小值策略v6添加到数据库中"""
import os
import sys
import json
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE = os.path.dirname(os.path.dirname(__file__))
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
        'code': s.code[:200] + '...' if s.code and len(s.code) > 200 else s.code  # 只备份代码前200字符
    })
backup_path = os.path.join(backup_dir, f'strategies_backup_{now}.json')
with open(backup_path, 'w', encoding='utf-8') as f:
    json.dump(strategies_data, f, ensure_ascii=False, indent=2)
print('Backed up strategies to', backup_path)

# 2) 读取 v6 源码
strategy_file = os.path.join(BASE, 'src', 'backend', 'strategy', 'extremum_strategy_v6.py')
with open(strategy_file, 'r', encoding='utf-8') as f:
    code = f.read()

print(f"已读取策略代码文件: {strategy_file}")
print(f"代码长度: {len(code)} 字符")

# 3) 检查是否已存在 v6 策略
target = session.query(StrategyModel).filter(StrategyModel.template == 'extremum_v6').first()
if not target:
    target = session.query(StrategyModel).filter(StrategyModel.name == '极大极小值策略v6').first()

if target:
    print(f'策略已存在，ID: {target.id}, 名称: {target.name}')
    print('正在更新现有策略代码...')
    target.code = code
    target.updated_at = datetime.datetime.now()
    try:
        session.commit()
        print(f'Updated existing strategy ID: {target.id}')
    except Exception as e:
        session.rollback()
        print(f'Failed to update strategy: {e}')
else:
    # 如果没有则插入新策略
    print('创建新的极大极小值策略v6...')
    s = StrategyModel(
        name='极大极小值策略v6',
        description='增强版极值识别策略，采用多条件组合识别极值：均线交叉、趋势转折、RSI确认、成交量放大等',
        code=code,
        parameters=json.dumps({
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
            
            # 仓位管理参数
            "base_position_size": 0.2,
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
        }),
        template='extremum_v6',
        is_template=True,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    )
    session.add(s)
    session.flush()
    try:
        session.commit()
        print(f'Inserted new extremum strategy v6, ID: {s.id}')
    except Exception as e:
        session.rollback()
        print(f'Failed to insert strategy: {e}')

print('Done')