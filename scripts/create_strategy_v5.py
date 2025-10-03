#!/usr/bin/env python3
import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 调整为项目 sqlite 路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backtesting.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

# 导入模型
StrategyModel = __import__('src.backend.models.strategy', fromlist=['Strategy']).Strategy

# 读取策略代码
strategy_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'backend', 'strategy', 'extremum_strategy_v5.py')
with open(strategy_file, 'r', encoding='utf-8') as f:
    code = f.read()

# 备份代码到 data/backup
now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'backup')
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)
backup_path = os.path.join(backup_dir, f'strategy_v5_backup_{now}.py')
with open(backup_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('已备份 v5 源码到:', backup_path)

# 检查是否已存在同名模板
existing = session.query(StrategyModel).filter(StrategyModel.name == '极大极小值策略v5').first()
if existing:
    print('已存在 v5 策略，ID:', existing.id)
else:
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
    print('已插入新模板，ID:', s.id)
