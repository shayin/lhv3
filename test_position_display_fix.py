#!/usr/bin/env python3
"""
测试仓位显示修复效果
验证增强型MA策略分批建仓后的仓位显示是否正确
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.backend.strategy.enhanced_ma_strategy import EnhancedMAStrategy
from src.backend.backtest.engine import BacktestEngine

def create_test_data():
    """创建测试数据，包含明显的MA交叉信号"""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    n_days = len(dates)
    
    # 创建价格数据，包含多个趋势阶段
    prices = []
    base_price = 100.0
    
    for i in range(n_days):
        # 创建不同的价格趋势阶段
        if i < 50:  # 横盘整理
            price = base_price + np.random.normal(0, 1)
        elif i < 100:  # 缓慢上涨 - 触发第一阶段买入
            price = base_price + (i - 50) * 0.5 + np.random.normal(0, 1)
        elif i < 150:  # 加速上涨 - 触发第二阶段买入
            price = base_price + 25 + (i - 100) * 1.0 + np.random.normal(0, 1)
        elif i < 200:  # 高位震荡
            price = base_price + 75 + np.random.normal(0, 2)
        elif i < 250:  # 开始下跌 - 触发第一阶段卖出
            price = base_price + 75 - (i - 200) * 0.8 + np.random.normal(0, 1)
        else:  # 继续下跌 - 触发第二阶段卖出
            price = base_price + 35 - (i - 250) * 0.3 + np.random.normal(0, 1)
        
        prices.append(max(price, 10))  # 确保价格不会太低
    
    # 创建OHLCV数据
    data = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
        'low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, n_days)
    })
    
    return data

def test_position_display():
    """测试仓位显示修复效果"""
    print("=== 测试仓位显示修复效果 ===")
    
    # 1. 创建测试数据
    print("1. 创建测试数据...")
    test_data = create_test_data()
    print(f"   测试数据: {len(test_data)} 天")
    
    # 2. 初始化增强MA策略
    print("2. 初始化增强MA策略...")
    strategy_params = {
        "n1": 5,    # 短期MA
        "n2": 10,   # 中期MA  
        "n3": 20,   # 长期MA
        "position_per_stage": 0.25,  # 每阶段25%
    }
    
    strategy = EnhancedMAStrategy(
        name="增强版MA策略测试",
        data=test_data,
        parameters=strategy_params
    )
    
    # 3. 生成交易信号
    print("3. 生成交易信号...")
    signals = strategy.generate_signals()
    buy_signals = signals[signals['signal'] == 1]
    sell_signals = signals[signals['signal'] == -1]
    
    print(f"   买入信号: {len(buy_signals)} 个")
    print(f"   卖出信号: {len(sell_signals)} 个")
    
    if len(buy_signals) > 0:
        print("   买入信号详情:")
        for idx, row in buy_signals.head(5).iterrows():
            print(f"     {row['date']}: 价格={row['close']:.2f}, 仓位={row.get('position_size', 0.25)*100:.0f}%")
    
    # 4. 运行回测
    print("4. 运行回测...")
    backtest_engine = BacktestEngine(
        data=test_data,
        strategy=strategy,
        initial_capital=100000.0
    )
    
    # 设置分批建仓参数
    backtest_engine.set_parameters({
        'positionConfig': {
            'mode': 'staged',
            'sizes': [0.25, 0.25, 0.25, 0.25]  # 4个阶段，每个25%
        }
    })
    
    results = backtest_engine.run()
    
    # 5. 分析交易记录
    print("5. 分析交易记录...")
    trades = results.get('trades', [])
    
    if not trades:
        print("   ❌ 没有交易记录生成")
        return
    
    print(f"   总交易次数: {len(trades)}")
    
    # 分析买入交易
    buy_trades = [t for t in trades if t['action'] == 'BUY']
    sell_trades = [t for t in trades if t['action'] == 'SELL']
    
    print(f"   买入交易: {len(buy_trades)} 次")
    print(f"   卖出交易: {len(sell_trades)} 次")
    
    if buy_trades:
        print("\n   买入交易详情:")
        print("   日期        | 价格   | 单次仓位 | 累计仓位 | 持股数量 | 触发原因")
        print("   " + "-" * 80)
        
        for trade in buy_trades:
            date = trade['date']
            price = trade['price']
            single_pos = trade.get('position_size', 0) * 100
            cumulative_pos = trade.get('cumulative_position_ratio', 0) * 100
            total_shares = trade.get('total_shares', 0)
            reason = trade.get('trigger_reason', '')[:20]
            
            print(f"   {date} | {price:6.2f} | {single_pos:7.1f}% | {cumulative_pos:7.1f}% | {total_shares:8.0f} | {reason}")
    
    if sell_trades:
        print("\n   卖出交易详情:")
        print("   日期        | 价格   | 单次仓位 | 累计仓位 | 剩余股数 | 触发原因")
        print("   " + "-" * 80)
        
        for trade in sell_trades:
            date = trade['date']
            price = trade['price']
            single_pos = trade.get('position_size', 0) * 100
            cumulative_pos = trade.get('cumulative_position_ratio', 0) * 100
            total_shares = trade.get('total_shares', 0)
            reason = trade.get('trigger_reason', '')[:20]
            
            print(f"   {date} | {price:6.2f} | {single_pos:7.1f}% | {cumulative_pos:7.1f}% | {total_shares:8.0f} | {reason}")
    
    # 6. 验证修复效果
    print("\n6. 验证修复效果...")
    
    # 检查是否有多次买入且累计仓位递增
    if len(buy_trades) >= 2:
        cumulative_positions = [t.get('cumulative_position_ratio', 0) * 100 for t in buy_trades]
        is_increasing = all(cumulative_positions[i] >= cumulative_positions[i-1] for i in range(1, len(cumulative_positions)))
        
        if is_increasing:
            print("   ✅ 累计仓位正确递增")
            max_position = max(cumulative_positions)
            print(f"   ✅ 最大累计仓位: {max_position:.1f}%")
            
            if max_position > 25:
                print("   ✅ 成功实现分批建仓，累计仓位超过单次25%限制")
            else:
                print("   ⚠️  累计仓位未超过25%，可能仍有问题")
        else:
            print("   ❌ 累计仓位未正确递增")
            print(f"   累计仓位序列: {cumulative_positions}")
    else:
        print("   ⚠️  买入交易次数不足，无法验证分批建仓")
    
    # 检查单次仓位是否都是25%
    single_positions = [t.get('position_size', 0) * 100 for t in buy_trades]
    if all(abs(pos - 25.0) < 1.0 for pos in single_positions):
        print("   ✅ 单次交易仓位都是25%")
    else:
        print(f"   ❌ 单次交易仓位不一致: {single_positions}")
    
    print("\n=== 测试完成 ===")
    
    return {
        'total_trades': len(trades),
        'buy_trades': len(buy_trades),
        'sell_trades': len(sell_trades),
        'max_cumulative_position': max([t.get('cumulative_position_ratio', 0) * 100 for t in buy_trades]) if buy_trades else 0
    }

if __name__ == "__main__":
    test_results = test_position_display()
    
    print(f"\n总结:")
    print(f"- 总交易次数: {test_results['total_trades']}")
    print(f"- 买入次数: {test_results['buy_trades']}")
    print(f"- 卖出次数: {test_results['sell_trades']}")
    print(f"- 最大累计仓位: {test_results['max_cumulative_position']:.1f}%")
    
    if test_results['max_cumulative_position'] > 25:
        print("🎉 仓位显示修复成功！")
    else:
        print("❌ 仓位显示仍有问题")