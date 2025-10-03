#!/usr/bin/env python3
import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:////Users/shayin/data1/htdocs/project/joy/lhv3/backtesting.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

StrategyModel = __import__('src.backend.models.strategy', fromlist=['Strategy']).Strategy

strategy_id = 5
strategy = session.query(StrategyModel).filter(StrategyModel.id==strategy_id).first()
if not strategy:
    print('策略未找到:', strategy_id)
    raise SystemExit(1)

code = strategy.code
if isinstance(code, (bytes, bytearray)):
    try:
        code = code.decode('utf-8')
    except Exception:
        code = code.decode('latin-1')

# 备份原始代码到 data/backup
now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'backup')
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)
backup_path = os.path.join(backup_dir, f'strategy_{strategy_id}_backup_{now}.py')
with open(backup_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('已备份原始策略到:', backup_path)

# 生成patched code（只做明确替换）
patched = code.replace('for i in range(len(df)):', 'for i in range(len(prices)):')

if patched == code:
    print('警告：没有检测到要替换的字符串。请人工检查备份文件。')
else:
    # 更新数据库中的策略代码
    strategy.code = patched
    try:
        from datetime import datetime
        strategy.updated_at = datetime.now()
    except Exception:
        pass
    session.add(strategy)
    session.commit()
    print('已在数据库中更新策略代码（ID=', strategy_id, ')')
    print('如需回滚，请使用备份文件替换 code 字段。')
