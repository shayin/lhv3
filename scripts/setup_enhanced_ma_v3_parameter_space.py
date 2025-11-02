#!/usr/bin/env python3
"""
为增强型MA策略V3设置参数空间
"""

import sys
import os
import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.models.strategy_parameter_space import StrategyParameterSpace

def setup_parameter_space():
    """为增强型MA策略V3设置参数空间"""
    
    # 数据库连接
    db_path = os.path.join(project_root, 'backtesting.db')
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print(f"连接到数据库: {db_path}")
    
    # 策略ID - 增强型MA策略V3
    strategy_id = 12
    
    # 删除现有的参数空间配置（如果存在）
    existing_spaces = session.query(StrategyParameterSpace).filter(
        StrategyParameterSpace.strategy_id == strategy_id
    ).all()
    
    if existing_spaces:
        print(f"删除现有的 {len(existing_spaces)} 个参数空间配置")
        for space in existing_spaces:
            session.delete(space)
    
    # 定义参数空间配置
    parameter_spaces = [
        {
            'parameter_name': 'n1',
            'parameter_type': 'int',
            'min_value': 3,
            'max_value': 15,
            'step_size': 1,
            'description': '短期移动平均线周期'
        },
        {
            'parameter_name': 'n2',
            'parameter_type': 'int',
            'min_value': 10,
            'max_value': 30,
            'step_size': 5,
            'description': '中期移动平均线周期'
        },
        {
            'parameter_name': 'n3',
            'parameter_type': 'int',
            'min_value': 20,
            'max_value': 50,
            'step_size': 5,
            'description': '长期移动平均线周期'
        },
        {
            'parameter_name': 'position_per_stage',
            'parameter_type': 'float',
            'min_value': 0.1,
            'max_value': 0.5,
            'step_size': 0.1,
            'description': '每阶段建仓比例'
        },
        {
            'parameter_name': 'max_total_position',
            'parameter_type': 'float',
            'min_value': 0.5,
            'max_value': 1.0,
            'step_size': 0.1,
            'description': '最大总仓位'
        }
    ]
    
    # 添加参数空间配置
    for space_config in parameter_spaces:
        space = StrategyParameterSpace(
            strategy_id=strategy_id,
            parameter_name=space_config['parameter_name'],
            parameter_type=space_config['parameter_type'],
            min_value=space_config['min_value'],
            max_value=space_config['max_value'],
            step_size=space_config['step_size'],
            description=space_config['description'],
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        )
        session.add(space)
    
    try:
        session.commit()
        print(f"成功添加 {len(parameter_spaces)} 个参数空间配置")
    except Exception as e:
        session.rollback()
        print(f"添加参数空间配置失败: {e}")
    
    session.close()
    print('完成')

if __name__ == "__main__":
    setup_parameter_space()