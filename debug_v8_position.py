#!/usr/bin/env python3
"""
调试v8策略卖出0股的问题
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from backend.strategy.extremum_strategy_v8 import ExtremumStrategyV8

def test_position_calculation():
    """测试仓位计算逻辑"""
    
    # 创建策略实例
    strategy = ExtremumStrategyV8()
    
    # 测试参数
    test_cases = [
        {
            'signal_strength': 0.8,
            'current_position': 0.0,
            'signal_type': 'buy',
            'description': '买入信号，当前无仓位'
        },
        {
            'signal_strength': 0.8,
            'current_position': 0.1,
            'signal_type': 'sell',
            'description': '卖出信号，当前仓位0.1'
        },
        {
            'signal_strength': 0.7,
            'current_position': 0.05,
            'signal_type': 'sell',
            'description': '卖出信号，当前仓位0.05'
        },
        {
            'signal_strength': 0.9,
            'current_position': 0.02,
            'signal_type': 'sell',
            'description': '卖出信号，当前仓位0.02'
        }
    ]
    
    print("=== V8策略仓位计算测试 ===")
    print(f"默认参数:")
    print(f"  base_position_size: {strategy.parameters.get('base_position_size', 0.05)}")
    print(f"  max_position_ratio: {strategy.parameters.get('max_position_ratio', 0.8)}")
    print(f"  position_scaling: {strategy.parameters.get('position_scaling', True)}")
    print()
    
    for i, case in enumerate(test_cases, 1):
        print(f"测试案例 {i}: {case['description']}")
        print(f"  输入: signal_strength={case['signal_strength']}, current_position={case['current_position']}, signal_type='{case['signal_type']}'")
        
        position_size = strategy.calculate_position_size(
            case['signal_strength'], 
            case['current_position'], 
            case['signal_type']
        )
        
        print(f"  输出: position_size={position_size}")
        
        # 分析计算过程
        base_size = strategy.parameters.get("base_position_size", 0.05)
        scaled_size = base_size * case['signal_strength']
        
        print(f"  计算过程:")
        print(f"    base_size = {base_size}")
        print(f"    scaled_size = base_size * signal_strength = {base_size} * {case['signal_strength']} = {scaled_size}")
        
        if case['signal_type'] == 'sell':
            min_result = min(scaled_size, case['current_position'])
            print(f"    卖出: min(scaled_size, current_position) = min({scaled_size}, {case['current_position']}) = {min_result}")
            
            if min_result == 0:
                print(f"    ❌ 问题发现: 卖出仓位为0!")
                if scaled_size > case['current_position']:
                    print(f"       原因: scaled_size ({scaled_size}) > current_position ({case['current_position']})")
                    print(f"       建议: 应该卖出 current_position 的一部分，而不是0")
        
        print()

if __name__ == "__main__":
    test_position_calculation()