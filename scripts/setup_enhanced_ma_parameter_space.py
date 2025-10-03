#!/usr/bin/env python3
"""为增强型移动平均策略配置参数调优空间"""
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

def setup_enhanced_ma_parameter_space():
    """为增强型移动平均策略设置参数空间"""
    
    # 查找增强型移动平均策略
    strategy = session.query(Strategy).filter(Strategy.template == 'enhanced_ma').first()
    if not strategy:
        print("错误: 未找到增强型移动平均策略")
        return
    
    print(f"找到策略: {strategy.name} (ID: {strategy.id})")
    
    # 删除现有的参数空间配置（如果存在）
    existing_spaces = session.query(StrategyParameterSpace).filter(
        StrategyParameterSpace.strategy_id == strategy.id
    ).all()
    
    if existing_spaces:
        print(f"删除现有的 {len(existing_spaces)} 个参数空间配置")
        for space in existing_spaces:
            session.delete(space)
    
    # 定义参数空间配置
    parameter_spaces = [
        {
            'parameter_name': 'short_window',
            'parameter_type': 'int',
            'min_value': 3,
            'max_value': 15,
            'step_size': 1,
            'description': '短期移动平均线窗口期'
        },
        {
            'parameter_name': 'long_window',
            'parameter_type': 'int',
            'min_value': 15,
            'max_value': 50,
            'step_size': 5,
            'description': '长期移动平均线窗口期'
        },
        {
            'parameter_name': 'max_total_position',
            'parameter_type': 'float',
            'min_value': 0.5,
            'max_value': 1.0,
            'step_size': 0.1,
            'description': '最大总仓位比例'
        },
        {
            'parameter_name': 'stage1_position',
            'parameter_type': 'float',
            'min_value': 0.1,
            'max_value': 0.5,
            'step_size': 0.1,
            'description': '第一阶段建仓比例'
        },
        {
            'parameter_name': 'stage2_position',
            'parameter_type': 'float',
            'min_value': 0.4,
            'max_value': 0.8,
            'step_size': 0.1,
            'description': '第二阶段建仓比例'
        },
        {
            'parameter_name': 'rsi_period',
            'parameter_type': 'int',
            'min_value': 10,
            'max_value': 20,
            'step_size': 2,
            'description': 'RSI指标计算周期'
        },
        {
            'parameter_name': 'rsi_oversold',
            'parameter_type': 'int',
            'min_value': 20,
            'max_value': 35,
            'step_size': 5,
            'description': 'RSI超卖阈值'
        },
        {
            'parameter_name': 'rsi_overbought',
            'parameter_type': 'int',
            'min_value': 65,
            'max_value': 80,
            'step_size': 5,
            'description': 'RSI超买阈值'
        },
        {
            'parameter_name': 'volume_threshold',
            'parameter_type': 'float',
            'min_value': 1.0,
            'max_value': 2.0,
            'step_size': 0.2,
            'description': '成交量确认阈值倍数'
        },
        {
            'parameter_name': 'stop_loss',
            'parameter_type': 'float',
            'min_value': 0.02,
            'max_value': 0.10,
            'step_size': 0.01,
            'description': '止损比例'
        },
        {
            'parameter_name': 'take_profit',
            'parameter_type': 'float',
            'min_value': 0.08,
            'max_value': 0.25,
            'step_size': 0.02,
            'description': '止盈比例'
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
    
    # 创建默认参数组
    default_params = {
        "short_window": 5,
        "long_window": 20,
        "max_total_position": 1.0,
        "stage1_position": 0.3,
        "stage2_position": 0.7,
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "volume_threshold": 1.2,
        "stop_loss": 0.05,
        "take_profit": 0.15
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
            name='增强型移动平均策略-默认参数',
            description='增强型移动平均策略的默认参数配置',
            parameters=default_params,
            is_default=True,
            status='active'
        )
        session.add(default_set)
    
    # 提交所有更改
    try:
        session.commit()
        print(f"成功创建 {len(created_spaces)} 个参数空间配置")
        print("参数空间配置完成!")
        
        # 显示创建的参数空间
        print("\n创建的参数空间:")
        for space in created_spaces:
            if space.parameter_type in ['int', 'float']:
                print(f"- {space.parameter_name}: {space.min_value} ~ {space.max_value} (步长: {space.step_size})")
            else:
                print(f"- {space.parameter_name}: {space.choices}")
                
    except Exception as e:
        session.rollback()
        print(f"配置参数空间时发生错误: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    setup_enhanced_ma_parameter_space()