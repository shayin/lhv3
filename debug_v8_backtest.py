#!/usr/bin/env python3
"""
调试v8策略实际回测中卖出0股的问题
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from backend.strategy.extremum_strategy_v8 import ExtremumStrategyV8

def load_test_data():
    """加载测试数据"""
    try:
        # 尝试加载扩展的demo数据
        data_path = "/Users/shayin/data1/htdocs/project/joy/lhv3/data/demo/AAPL_extended.csv"
        df = pd.read_csv(data_path)
        
        # 确保数据格式正确
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        elif 'Date' in df.columns:
            df['date'] = pd.to_datetime(df['Date'])
            
        # 标准化列名
        column_mapping = {
            'Date': 'date',
            'Open': 'open', 
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]
        
        # 确保必要的列存在
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                print(f"警告: 缺少必要列 {col}")
                return None
        
        # 取所有数据进行测试
        df = df.copy()
        df = df.reset_index(drop=True)
        
        print(f"成功加载测试数据: {len(df)} 行")
        print(f"数据范围: {df['date'].min()} 到 {df['date'].max()}")
        print(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
        
        return df
        
    except Exception as e:
        print(f"加载数据失败: {e}")
        return None

def debug_v8_strategy():
    """调试v8策略的实际运行"""
    
    # 加载测试数据
    data = load_test_data()
    if data is None:
        return
    
    # 创建策略实例
    strategy = ExtremumStrategyV8(data=data)
    
    print("\n=== V8策略参数 ===")
    for key, value in strategy.parameters.items():
        print(f"  {key}: {value}")
    
    # 生成信号
    print("\n=== 生成交易信号 ===")
    try:
        signals_df = strategy.generate_signals()
        
        if signals_df is None or signals_df.empty:
            print("❌ 未生成任何信号")
            return
        
        print(f"生成信号数据: {len(signals_df)} 行")
        
        # 分析信号
        buy_signals = signals_df[signals_df['signal'] == 1]
        sell_signals = signals_df[signals_df['signal'] == -1]
        
        print(f"\n买入信号数量: {len(buy_signals)}")
        print(f"卖出信号数量: {len(sell_signals)}")
        
        # 检查卖出信号的仓位大小
        if len(sell_signals) > 0:
            print(f"\n=== 卖出信号详情 ===")
            for idx, row in sell_signals.iterrows():
                print(f"日期: {row.get('date', 'N/A')}")
                print(f"  信号强度: {row['signal_strength']:.3f}")
                print(f"  仓位大小: {row['position_size']:.6f}")
                print(f"  触发原因: {row['trigger_reason']}")
                print(f"  当前价格: {row['close']:.2f}")
                
                # 如果仓位大小为0，分析原因
                if row['position_size'] == 0:
                    print(f"  ❌ 发现卖出0股的情况!")
                    
                    # 手动计算应该的仓位大小
                    signal_strength = row['signal_strength']
                    base_size = strategy.parameters.get("base_position_size", 0.05)
                    scaled_size = base_size * signal_strength
                    
                    print(f"  分析:")
                    print(f"    base_position_size: {base_size}")
                    print(f"    signal_strength: {signal_strength}")
                    print(f"    scaled_size: {scaled_size}")
                    print(f"    需要检查当时的current_position值")
                
                print()
        
        # 显示前几行和后几行数据
        print(f"\n=== 信号数据样本 ===")
        display_cols = ['date', 'close', 'signal', 'signal_strength', 'position_size', 'trigger_reason']
        available_cols = [col for col in display_cols if col in signals_df.columns]
        
        print("前5行:")
        print(signals_df[available_cols].head().to_string(index=False))
        
        if len(signals_df) > 10:
            print("\n后5行:")
            print(signals_df[available_cols].tail().to_string(index=False))
        
        # 保存调试数据
        debug_file = "/Users/shayin/data1/htdocs/project/joy/lhv3/debug_v8_signals.csv"
        signals_df.to_csv(debug_file, index=False)
        print(f"\n调试数据已保存到: {debug_file}")
        
    except Exception as e:
        print(f"❌ 策略运行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_v8_strategy()