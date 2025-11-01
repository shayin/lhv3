#!/usr/bin/env python3
"""将增强型移动平均策略V2添加到数据库中"""
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

# 2) 读取增强型移动平均策略V2源码
strategy_file = os.path.join(BASE, 'src', 'backend', 'strategy', 'enhanced_ma_strategy_v2.py')
with open(strategy_file, 'r', encoding='utf-8') as f:
    code = f.read()

# 3) 查找是否已存在该策略（优先使用 template 字段，其次使用 name）
target = session.query(StrategyModel).filter(StrategyModel.template == 'enhanced_ma_v2').first()
if not target:
    target = session.query(StrategyModel).filter(StrategyModel.name == '增强型移动平均策略V2').first()

# 4) 默认参数配置 - 基于总资金的百分比
default_parameters = json.dumps({
    # MA周期参数
    "n1": 5,
    "n2": 10,
    "n3": 20,
    
    # 分批建仓参数 - 基于总资金的百分比
    "position_per_stage": 0.25,  # 每阶段建仓比例（总资金的25%）
    "max_total_position": 1.0,   # 最大总仓位（总资金的100%）
    
    # 信号确认参数
    "signal_confirmation_bars": 1,
    "enable_position_tracking": True,
    
    # V2特有标识
    "version": "V2",
    "position_calculation_method": "基于总资金的百分比"
}, ensure_ascii=False)

if not target:
    # 创建新策略
    print('Creating new enhanced MA strategy V2...')
    s = StrategyModel(
        name='增强型移动平均策略V2',
        description='基于移动平均线的增强型策略V2版本，采用基于总资金百分比的分批建仓和减仓策略，而非基于当前持仓的百分比',
        code=code,
        parameters=default_parameters,
        template='enhanced_ma_v2',
        is_template=True,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    )
    session.add(s)
    session.flush()
    session.commit()
    print('Inserted new enhanced MA strategy V2, ID:', s.id)
else:
    # 更新现有策略
    print('Updating existing enhanced MA strategy V2 ID:', target.id)
    target.code = code
    target.description = '基于移动平均线的增强型策略V2版本，采用基于总资金百分比的分批建仓和减仓策略，而非基于当前持仓的百分比'
    target.parameters = default_parameters
    target.updated_at = datetime.datetime.now()
    try:
        session.commit()
        print('Updated enhanced MA strategy V2 ID:', target.id)
    except Exception as e:
        session.rollback()
        print('Failed to update strategy:', e)

# 5) 显示策略对比信息
print("\n=== 策略版本对比 ===")
print("V1版本: 分批加仓和减仓时，以当前持仓的xx%来当做一份份买卖")
print("V2版本: 分批加仓和减仓时，以整个资金的xx%来当做一份份买卖")
print("\n例如：")
print("- V1: 当前持仓50万，每次交易当前持仓的25% = 12.5万")
print("- V2: 总资金100万，每次交易总资金的25% = 25万")
print("\nV2版本的优势：")
print("1. 仓位管理更加稳定，不受当前持仓波动影响")
print("2. 交易金额固定，便于资金规划")
print("3. 风险控制更加精确")

session.close()
print('\nDone')