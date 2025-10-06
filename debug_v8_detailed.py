#!/usr/bin/env python3
"""
详细调试v8策略为什么没有生成信号
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from backend.strategy.extremum_strategy_v8 import ExtremumStrategyV8

def debug_strategy_step_by_step():
    """逐步调试策略执行过程"""
    
    # 加载测试数据
    data_path = "/Users/shayin/data1/htdocs/project/joy/lhv3/data/demo/AAPL_extended.csv"
    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    
    print(f"加载数据: {len(df)} 行")
    print(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
    
    # 创建策略实例
    strategy = ExtremumStrategyV8(data=df)
    
    # 1. 检查指标计算
    print("\n=== 1. 检查指标计算 ===")
    df_with_indicators = strategy.calculate_indicators()
    
    print(f"计算指标后数据: {len(df_with_indicators)} 行")
    print("指标列:", [col for col in df_with_indicators.columns if col not in ['date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']])
    
    # 检查RSI值
    if 'rsi' in df_with_indicators.columns:
        rsi_stats = df_with_indicators['rsi'].describe()
        print(f"RSI统计: min={rsi_stats['min']:.1f}, max={rsi_stats['max']:.1f}, mean={rsi_stats['mean']:.1f}")
    
    # 2. 检查极值识别
    print("\n=== 2. 检查极值识别 ===")
    
    # 手动测试几个时间点的极值识别
    test_indices = [15, 30, 45]  # 测试几个时间点
    
    for test_idx in test_indices:
        if test_idx < len(df_with_indicators):
            print(f"\n测试第{test_idx}天 ({df_with_indicators.iloc[test_idx]['date'].strftime('%Y-%m-%d')}):")
            
            minima_candidates, maxima_candidates = strategy.identify_extremum_candidates(df_with_indicators, test_idx)
            
            print(f"  极小值候选: {minima_candidates}")
            print(f"  极大值候选: {maxima_candidates}")
            
            # 检查信号强度
            for extremum_idx in minima_candidates:
                strength = strategy.calculate_signal_strength(df_with_indicators, extremum_idx, 'min', test_idx)
                print(f"  极小值{extremum_idx}强度: {strength:.3f}")
                
            for extremum_idx in maxima_candidates:
                strength = strategy.calculate_signal_strength(df_with_indicators, extremum_idx, 'max', test_idx)
                print(f"  极大值{extremum_idx}强度: {strength:.3f}")
    
    # 3. 检查市场环境过滤
    print("\n=== 3. 检查市场环境过滤 ===")
    
    market_ok_count = 0
    for i in range(len(df_with_indicators)):
        if strategy.check_market_environment(df_with_indicators, i):
            market_ok_count += 1
    
    print(f"通过市场环境检查的天数: {market_ok_count}/{len(df_with_indicators)}")
    
    # 4. 检查信号强度阈值
    print(f"\n=== 4. 检查参数设置 ===")
    print(f"信号强度阈值: {strategy.parameters.get('signal_strength_threshold', 0.65)}")
    print(f"最小价格变化: {strategy.parameters.get('min_price_change_pct', 0.03)}")
    print(f"极值确认天数: {strategy.parameters.get('extremum_confirm_days', 3)}")
    
    # 5. 降低阈值重新测试
    print(f"\n=== 5. 降低阈值重新测试 ===")
    
    # 临时降低阈值
    original_threshold = strategy.parameters['signal_strength_threshold']
    original_min_change = strategy.parameters['min_price_change_pct']
    
    strategy.parameters['signal_strength_threshold'] = 0.3  # 降低到0.3
    strategy.parameters['min_price_change_pct'] = 0.01      # 降低到1%
    
    print(f"临时调整参数:")
    print(f"  signal_strength_threshold: {original_threshold} -> {strategy.parameters['signal_strength_threshold']}")
    print(f"  min_price_change_pct: {original_min_change} -> {strategy.parameters['min_price_change_pct']}")
    
    # 重新生成信号
    signals_df = strategy.generate_signals()
    
    buy_signals = signals_df[signals_df['signal'] == 1]
    sell_signals = signals_df[signals_df['signal'] == -1]
    
    print(f"\n降低阈值后:")
    print(f"买入信号数量: {len(buy_signals)}")
    print(f"卖出信号数量: {len(sell_signals)}")
    
    if len(buy_signals) > 0:
        print("\n买入信号详情:")
        for idx, row in buy_signals.head(3).iterrows():
            print(f"  {row['date'].strftime('%Y-%m-%d')}: 强度{row['signal_strength']:.3f}, 仓位{row['position_size']:.4f}")
    
    if len(sell_signals) > 0:
        print("\n卖出信号详情:")
        for idx, row in sell_signals.head(3).iterrows():
            print(f"  {row['date'].strftime('%Y-%m-%d')}: 强度{row['signal_strength']:.3f}, 仓位{row['position_size']:.4f}")
            
            # 检查卖出0股的情况
            if row['position_size'] == 0:
                print(f"    ❌ 发现卖出0股!")
    
    # 恢复原始参数
    strategy.parameters['signal_strength_threshold'] = original_threshold
    strategy.parameters['min_price_change_pct'] = original_min_change

if __name__ == "__main__":
    debug_strategy_step_by_step()