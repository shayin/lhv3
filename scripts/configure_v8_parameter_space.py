#!/usr/bin/env python3
"""为极大极小值策略v8配置参数空间"""
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
from src.backend.models.strategy import Strategy
from src.backend.models.optimization import StrategyParameterSpace

# 查找 v8 策略
strategy = session.query(Strategy).filter(Strategy.template == 'extremum_v8').first()
if not strategy:
    strategy = session.query(Strategy).filter(Strategy.name == '极大极小值策略v8').first()

if not strategy:
    print('未找到极大极小值策略v8，请先将策略添加到数据库。')
    exit(1)

sid = strategy.id
print(f'找到策略: {strategy.name} (ID: {sid})')

# 备份现有参数空间
now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup_dir = os.path.join(BASE, 'data', 'backup')
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

existing = session.query(StrategyParameterSpace).filter(StrategyParameterSpace.strategy_id == sid).all()
if existing:
    backup_path = os.path.join(backup_dir, f'parameter_spaces_v8_backup_{now}.json')
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
            'description': e.description
        })
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
    print(f'备份现有参数空间到: {backup_path}')
    
    # 删除现有参数空间
    for e in existing:
        session.delete(e)
    session.commit()
    print(f'删除了 {len(existing)} 个现有参数空间')

# 定义 v8 策略的参数空间 - 基于v6但针对仓位管理改进进行优化
param_spaces = [
    # 极值识别基础参数
    {'parameter_name': 'lookback_period', 'parameter_type': 'int', 'min_value': 8, 'max_value': 25, 'step_size': 1, 'choices': None, 'description': '极值识别回望周期'},
    {'parameter_name': 'min_price_change_pct', 'parameter_type': 'float', 'min_value': 0.015, 'max_value': 0.06, 'step_size': 0.005, 'choices': None, 'description': '最小价格变化百分比'},
    {'parameter_name': 'extremum_confirm_days', 'parameter_type': 'int', 'min_value': 2, 'max_value': 6, 'step_size': 1, 'choices': None, 'description': '极值确认天数'},
    
    # 均线参数
    {'parameter_name': 'ma_short', 'parameter_type': 'int', 'min_value': 5, 'max_value': 15, 'step_size': 1, 'choices': None, 'description': '短期均线周期'},
    {'parameter_name': 'ma_long', 'parameter_type': 'int', 'min_value': 15, 'max_value': 40, 'step_size': 2, 'choices': None, 'description': '长期均线周期'},
    {'parameter_name': 'ma_cross_confirm', 'parameter_type': 'choice', 'min_value': None, 'max_value': None, 'step_size': None, 'choices': [True, False], 'description': '是否启用均线交叉确认'},
    
    # 趋势转折识别参数
    {'parameter_name': 'trend_reversal_points', 'parameter_type': 'int', 'min_value': 4, 'max_value': 8, 'step_size': 1, 'choices': None, 'description': '趋势转折判断点数'},
    {'parameter_name': 'reversal_threshold_pct', 'parameter_type': 'float', 'min_value': 0.01, 'max_value': 0.04, 'step_size': 0.005, 'choices': None, 'description': '转折阈值百分比'},
    
    # RSI参数
    {'parameter_name': 'rsi_period', 'parameter_type': 'int', 'min_value': 10, 'max_value': 18, 'step_size': 1, 'choices': None, 'description': 'RSI计算周期'},
    {'parameter_name': 'rsi_overbought', 'parameter_type': 'int', 'min_value': 68, 'max_value': 78, 'step_size': 2, 'choices': None, 'description': 'RSI超买阈值'},
    {'parameter_name': 'rsi_oversold', 'parameter_type': 'int', 'min_value': 22, 'max_value': 32, 'step_size': 2, 'choices': None, 'description': 'RSI超卖阈值'},
    {'parameter_name': 'rsi_confirm', 'parameter_type': 'choice', 'min_value': None, 'max_value': None, 'step_size': None, 'choices': [True, False], 'description': '是否启用RSI确认'},
    
    # 成交量确认参数
    {'parameter_name': 'volume_ma_period', 'parameter_type': 'int', 'min_value': 15, 'max_value': 25, 'step_size': 2, 'choices': None, 'description': '成交量均线周期'},
    {'parameter_name': 'volume_amplify_ratio', 'parameter_type': 'float', 'min_value': 1.3, 'max_value': 2.5, 'step_size': 0.1, 'choices': None, 'description': '成交量放大倍数'},
    {'parameter_name': 'volume_confirm', 'parameter_type': 'choice', 'min_value': None, 'max_value': None, 'step_size': None, 'choices': [True, False], 'description': '是否启用成交量确认'},
    
    # 信号强度参数
    {'parameter_name': 'signal_strength_threshold', 'parameter_type': 'float', 'min_value': 0.5, 'max_value': 0.85, 'step_size': 0.05, 'choices': None, 'description': '信号强度阈值'},
    {'parameter_name': 'max_signals_per_period', 'parameter_type': 'int', 'min_value': 2, 'max_value': 4, 'step_size': 1, 'choices': None, 'description': '每周期最大信号数'},
    
    # 仓位管理参数 - V8版本优化：更小的基础仓位，更精细的控制
    {'parameter_name': 'base_position_size', 'parameter_type': 'float', 'min_value': 0.03, 'max_value': 0.12, 'step_size': 0.01, 'choices': None, 'description': 'V8基础仓位大小（统一买卖）'},
    {'parameter_name': 'max_position_ratio', 'parameter_type': 'float', 'min_value': 0.6, 'max_value': 0.95, 'step_size': 0.05, 'choices': None, 'description': '最大仓位比例'},
    {'parameter_name': 'position_scaling', 'parameter_type': 'choice', 'min_value': None, 'max_value': None, 'step_size': None, 'choices': [True, False], 'description': '是否启用仓位缩放'},
    
    # 风险控制参数 - 针对V8的仓位管理改进进行调整
    {'parameter_name': 'stop_loss_pct', 'parameter_type': 'float', 'min_value': 0.03, 'max_value': 0.10, 'step_size': 0.01, 'choices': None, 'description': '止损百分比'},
    {'parameter_name': 'take_profit_pct', 'parameter_type': 'float', 'min_value': 0.10, 'max_value': 0.25, 'step_size': 0.02, 'choices': None, 'description': '止盈百分比'},
    {'parameter_name': 'trailing_stop_pct', 'parameter_type': 'float', 'min_value': 0.025, 'max_value': 0.07, 'step_size': 0.005, 'choices': None, 'description': '移动止损百分比'},
    {'parameter_name': 'max_hold_days', 'parameter_type': 'int', 'min_value': 15, 'max_value': 40, 'step_size': 5, 'choices': None, 'description': '最大持仓天数'},
    
    # 市场环境过滤参数
    {'parameter_name': 'market_trend_period', 'parameter_type': 'int', 'min_value': 40, 'max_value': 80, 'step_size': 10, 'choices': None, 'description': '市场趋势判断周期'},
    {'parameter_name': 'bear_market_threshold', 'parameter_type': 'float', 'min_value': -0.15, 'max_value': -0.08, 'step_size': 0.01, 'choices': None, 'description': '熊市阈值'},
    {'parameter_name': 'bull_market_threshold', 'parameter_type': 'float', 'min_value': 0.08, 'max_value': 0.15, 'step_size': 0.01, 'choices': None, 'description': '牛市阈值'}
]

# 插入参数空间配置
inserted = []
for p in param_spaces:
    ps = StrategyParameterSpace(
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
    inserted.append(ps)

session.commit()
print(f'成功插入 {len(inserted)} 个参数空间配置')

# 显示插入的配置
print('\n插入的参数空间配置:')
for i, ps in enumerate(inserted, 1):
    print(f'{i:2d}. {ps.parameter_name:25s} | {ps.parameter_type:6s} | {ps.description}')
    if ps.parameter_type in ['int', 'float']:
        print(f'     范围: [{ps.min_value}, {ps.max_value}], 步长: {ps.step_size}')
    elif ps.parameter_type == 'choice':
        print(f'     选项: {ps.choices}')

session.close()
print('\nV8策略参数空间配置完成！')
print('主要改进：')
print('- 基础仓位大小范围更精细：0.03-0.12（步长0.01）')
print('- 针对统一买卖仓位管理进行优化')
print('- 调整了风险控制参数以适应新的仓位管理方式')