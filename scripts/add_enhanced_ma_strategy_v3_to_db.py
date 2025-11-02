#!/usr/bin/env python3
"""
将增强型MA策略V3添加到数据库
"""

import sys
import os
import json
import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.models.strategy import Strategy as StrategyModel

def add_enhanced_ma_strategy_v3_to_db():
    """将增强型MA策略V3添加到数据库"""
    
    # 数据库连接
    db_path = os.path.join(project_root, 'backtesting.db')
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print(f"连接到数据库: {db_path}")
    
    # 策略代码文件路径
    strategy_file = os.path.join(project_root, 'src/backend/strategy/enhanced_ma_strategy_v3.py')
    
    # 读取策略代码
    with open(strategy_file, 'r', encoding='utf-8') as f:
        code = f.read()

    # 查找是否已存在该策略（优先使用 template 字段，其次使用 name）
    target = session.query(StrategyModel).filter(StrategyModel.template == 'enhanced_ma_v3').first()
    if not target:
        target = session.query(StrategyModel).filter(StrategyModel.name == '增强型移动平均策略V3').first()

    # 默认参数配置
    default_parameters = json.dumps({
        # MA周期参数
        "n1": 5,
        "n2": 10,
        "n3": 20,
        
        # 分批建仓参数
        "position_per_stage": 0.25,  # 每阶段建仓比例（25%）
        "max_total_position": 1.0,   # 最大总仓位（100%）
        
        # 信号确认参数
        "signal_confirmation_bars": 1,
        "enable_position_tracking": True,
        
        # V3特有标识
        "version": "V3",
        "optimization_enabled": True
    }, ensure_ascii=False)

    if not target:
        # 创建新策略
        print('创建新增强型MA策略V3...')
        s = StrategyModel(
            name='增强型移动平均策略V3',
            description='基于移动平均线的增强型策略V3版本，优化参数传递和处理，确保参数调优时不同参数能够正确应用',
            code=code,
            parameters=default_parameters,
            template='enhanced_ma_v3',
            is_template=True,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        )
        session.add(s)
        session.flush()
        session.commit()
        print('插入新增强型MA策略V3，ID:', s.id)
    else:
        # 更新现有策略
        print('更新现有增强型MA策略V3，ID:', target.id)
        target.code = code
        target.description = '基于移动平均线的增强型策略V3版本，优化参数传递和处理，确保参数调优时不同参数能够正确应用'
        target.parameters = default_parameters
        target.updated_at = datetime.datetime.now()
        try:
            session.commit()
            print('更新增强型MA策略V3，ID:', target.id)
        except Exception as e:
            session.rollback()
            print('更新策略失败:', e)

    # 设置参数空间
    setup_parameter_space(session, target.id if target else s.id)
    
    session.close()
    print('完成')

def setup_parameter_space(session, strategy_id):
    """为增强型MA策略V3设置参数空间"""
    from src.backend.models.strategy_parameter_space import StrategyParameterSpace
    
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

if __name__ == "__main__":
    add_enhanced_ma_strategy_v3_to_db()