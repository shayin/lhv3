#!/usr/bin/env python3
"""
将极大极小值策略v7添加到数据库
"""

import sys
import os
import json
import datetime

# 添加项目根目录到Python路径
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.models.strategy import Strategy as StrategyModel

# 数据库连接
DATABASE_URL = f"sqlite:///{BASE}/backtesting.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

print("正在添加极大极小值策略v7到数据库...")

# 1) 读取策略代码
strategy_file = os.path.join(BASE, 'src', 'backend', 'strategy', 'extremum_strategy_v7.py')
with open(strategy_file, 'r', encoding='utf-8') as f:
    code = f.read()

print(f"已读取策略代码文件: {strategy_file}")
print(f"代码长度: {len(code)} 字符")

# 2) 检查是否已存在 v7 策略
target = session.query(StrategyModel).filter(StrategyModel.template == 'extremum_v7').first()
if not target:
    target = session.query(StrategyModel).filter(StrategyModel.name == '极大极小值策略v7').first()

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
    print('创建新的极大极小值策略v7...')
    s = StrategyModel(
        name='极大极小值策略v7',
        description='参数化买卖比例版本，基于V6策略改进：支持可调节的买入比例和卖出比例参数，实现分批买入卖出优化',
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
            
            # V7新增：参数化买卖比例
            "buy_ratio": 0.2,           # 每次买入比例（相对于总资金）
            "sell_ratio": 0.5,          # 每次卖出比例（相对于当前持仓）
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
            "bull_market_threshold": 0.1,
        }),
        is_template=True,
        template='extremum_v7',
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    )
    
    try:
        session.add(s)
        session.commit()
        print(f'Successfully added strategy ID: {s.id}')
    except Exception as e:
        session.rollback()
        print(f'Failed to add strategy: {e}')

session.close()
print("完成！")