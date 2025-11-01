#!/usr/bin/env python3
"""为增强型移动平均策略V2配置参数调优空间（基于总资金百分比）"""
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
from src.backend.models.strategy import Strategy
from src.backend.models.optimization import StrategyParameterSpace, ParameterSet

def setup_enhanced_ma_v2_parameter_space():
    """为增强型移动平均策略V2设置参数空间"""
    # 查找增强型移动平均策略V2
    strategy = session.query(Strategy).filter(Strategy.template == 'enhanced_ma_v2').first()
    if not strategy:
        print("错误: 未找到增强型移动平均策略V2 (template=enhanced_ma_v2)")
        return False
    
    print(f"找到策略: {strategy.name} (ID: {strategy.id})")
    
    # 删除现有的参数空间配置（如果存在）
    existing_spaces = session.query(StrategyParameterSpace).filter(
        StrategyParameterSpace.strategy_id == strategy.id
    ).all()
    
    if existing_spaces:
        print(f"删除现有的 {len(existing_spaces)} 个参数空间配置")
        for space in existing_spaces:
            session.delete(space)
    
    # 定义参数空间配置（与V2代码参数一致）
    parameter_spaces = [
        {
            'parameter_name': 'n1',
            'parameter_type': 'int',
            'min_value': 3,
            'max_value': 15,
            'step_size': 1,
            'description': '短期MA周期（N1）'
        },
        {
            'parameter_name': 'n2',
            'parameter_type': 'int',
            'min_value': 8,
            'max_value': 25,
            'step_size': 1,
            'description': '中期MA周期（N2）'
        },
        {
            'parameter_name': 'n3',
            'parameter_type': 'int',
            'min_value': 15,
            'max_value': 60,
            'step_size': 1,
            'description': '长期MA周期（N3）'
        },
        {
            'parameter_name': 'position_per_stage',
            'parameter_type': 'float',
            'min_value': 0.1,
            'max_value': 0.5,
            'step_size': 0.05,
            'description': '每阶段仓位比例（相对于总资金）'
        },
        {
            'parameter_name': 'max_total_position',
            'parameter_type': 'float',
            'min_value': 0.5,
            'max_value': 1.0,
            'step_size': 0.1,
            'description': '最大总仓位比例（相对于总资金）'
        },
        {
            'parameter_name': 'signal_confirmation_bars',
            'parameter_type': 'int',
            'min_value': 1,
            'max_value': 3,
            'step_size': 1,
            'description': '信号确认所需K线数量'
        },
        {
            'parameter_name': 'enable_position_tracking',
            'parameter_type': 'bool',
            'choices': [True, False],
            'description': '是否启用仓位跟踪（优化时可禁用以降低开销）'
        }
    ]
    
    # 创建参数空间配置
    created_spaces = []
    for space_config in parameter_spaces:
        space = StrategyParameterSpace(
            strategy_id=strategy.id,
            **space_config
        )
        session.add(space)
        created_spaces.append(space)
    
    # 创建默认参数组（与V2代码默认一致）
    default_params = {
        "n1": 5,
        "n2": 10,
        "n3": 20,
        "position_per_stage": 0.25,
        "max_total_position": 1.0,
        "signal_confirmation_bars": 1,
        "enable_position_tracking": True,
        "version": "V2",
        "position_calculation_method": "基于总资金的百分比"
    }
    
    # 检查是否已存在默认参数组
    existing_default = session.query(ParameterSet).filter(
        ParameterSet.strategy_id == strategy.id,
        ParameterSet.is_default == True
    ).first()
    
    if existing_default:
        print(f"更新现有默认参数组: {existing_default.name}")
        existing_default.parameters = default_params
        existing_default.updated_at = datetime.datetime.utcnow()
    else:
        print("创建新的默认参数组")
        default_set = ParameterSet(
            strategy_id=strategy.id,
            name='增强型移动平均策略V2-默认参数',
            description='增强型移动平均策略V2的默认参数配置（基于总资金百分比）',
            parameters=default_params,
            is_default=True,
            status='active'
        )
        session.add(default_set)
    
    # 提交所有更改
    try:
        session.commit()
        print(f"成功创建 {len(created_spaces)} 个参数空间配置 (V2)")
        print("参数空间配置完成 (V2)!")
        
        # 显示创建的参数空间
        print("\n创建的参数空间 (V2):")
        for space in created_spaces:
            if space.parameter_type in ['int', 'float']:
                print(f"- {space.parameter_name}: {space.min_value} ~ {space.max_value} (步长: {space.step_size})")
            elif space.parameter_type == 'bool':
                print(f"- {space.parameter_name}: {space.choices}")
            else:
                print(f"- {space.parameter_name}: {getattr(space, 'choices', None)}")
        
        return True
    except Exception as e:
        session.rollback()
        print(f"配置参数空间时发生错误: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    setup_enhanced_ma_v2_parameter_space()