#!/usr/bin/env python3
"""
测试修复后的分批建仓功能
验证回测引擎是否能正确执行分批建仓和减仓
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.backend.strategy.enhanced_ma_strategy import EnhancedMAStrategy
from src.backend.backtest.engine import BacktestEngine

def create_test_data(days=100):
    """创建测试数据，设计特定的价格走势来触发分批建仓"""
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    
    # 创建一个明显的趋势变化来触发MA交叉信号
    base_price = 100
    prices = []
    
    for i in range(days):
        if i < 25:  # 前25天横盘整理
            price = base_price + np.random.normal(0, 0.5)
        elif i < 35:  # 25-35天快速上涨，触发N1上穿N2
            price = base_price + (i - 25) * 2.0 + np.random.normal(0, 0.3)
        elif i < 50:  # 35-50天继续上涨，触发N2上穿N3
            price = base_price + 10 * 2.0 + (i - 35) * 1.5 + np.random.normal(0, 0.4)
        elif i < 65:  # 50-65天高位整理
            price = base_price + 10 * 2.0 + 15 * 1.5 + np.random.normal(0, 0.6)
        elif i < 75:  # 65-75天开始下跌，触发N2下穿N3
            price = base_price + 10 * 2.0 + 15 * 1.5 - (i - 65) * 1.8 + np.random.normal(0, 0.5)
        else:  # 75天后继续下跌，触发N1下穿N2
            price = base_price + 10 * 2.0 + 15 * 1.5 - 10 * 1.8 - (i - 75) * 1.2 + np.random.normal(0, 0.4)
        
        prices.append(max(price, 50))  # 确保价格不低于50
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + np.random.uniform(0, 0.01)) for p in prices],
        'low': [p * (1 - np.random.uniform(0, 0.01)) for p in prices],
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, days)
    }, index=dates)
    
    return data

def test_staged_position_building():
    """测试分批建仓功能"""
    print("=" * 80)
    print("测试修复后的分批建仓功能")
    print("=" * 80)
    
    # 1. 创建测试数据
    print("1. 创建测试数据...")
    test_data = create_test_data(100)
    print(f"   测试数据: {len(test_data)} 天")
    print(f"   价格范围: {test_data['close'].min():.2f} - {test_data['close'].max():.2f}")
    
    # 2. 初始化策略
    print("\n2. 初始化增强版MA策略...")
    strategy_params = {
        'n1': 5,    # 短期MA
        'n2': 10,   # 中期MA
        'n3': 20,   # 长期MA
        'position_per_stage': 0.25,  # 每阶段25%
        'max_total_position': 1.0,   # 最大100%
    }
    
    strategy = EnhancedMAStrategy(parameters=strategy_params)
    strategy.set_data(test_data)
    print(f"   策略参数: N1={strategy_params['n1']}, N2={strategy_params['n2']}, N3={strategy_params['n3']}")
    
    # 3. 生成信号
    print("\n3. 生成交易信号...")
    signals = strategy.generate_signals()
    
    # 分析信号
    print("\n4. 信号分析:")
    total_signals = (signals['signal'] != 0).sum()
    buy_signals = (signals['signal'] == 1).sum()
    sell_signals = (signals['signal'] == -1).sum()
    
    print(f"   总信号数: {total_signals}")
    print(f"   买入信号: {buy_signals}")
    print(f"   卖出信号: {sell_signals}")
    
    # 阶段分析
    stage1_buy = (signals['stage'] == 'stage1_buy').sum()
    stage2_buy = (signals['stage'] == 'stage2_buy').sum()
    stage1_sell = (signals['stage'] == 'stage1_sell').sum()
    stage2_sell = (signals['stage'] == 'stage2_sell').sum()
    
    print(f"   阶段1建仓: {stage1_buy}")
    print(f"   阶段2建仓: {stage2_buy}")
    print(f"   阶段1减仓: {stage1_sell}")
    print(f"   阶段2减仓: {stage2_sell}")
    
    # 显示前几个信号
    signal_rows = signals[signals['signal'] != 0].head(10)
    if not signal_rows.empty:
        print("\n5. 前10个交易信号:")
        for idx, row in signal_rows.iterrows():
            signal_type = "买入" if row['signal'] == 1 else "卖出"
            print(f"   {idx.strftime('%Y-%m-%d')}: {signal_type} {row['position_size']:.1%} - {row['trigger_reason']}")
    
    # 4. 运行回测
    print("\n6. 运行回测...")
    backtest_engine = BacktestEngine(
        data=test_data,
        strategy=strategy,
        initial_capital=100000,
        commission_rate=0.001,
        slippage_rate=0.001
    )
    
    # 设置分批建仓参数
    backtest_engine.set_parameters({
        'positionConfig': {
            'mode': 'staged',
            'sizes': [0.25, 0.25, 0.25, 0.25]  # 分4次建仓，每次25%
        }
    })
    
    # 运行回测
    results = backtest_engine.run()
    
    # 5. 分析回测结果
    print("\n7. 回测结果分析:")
    print(f"   初始资金: {backtest_engine.initial_capital:,.2f}")
    print(f"   最终资金: {results.get('performance', {}).get('final_capital', 0):,.2f}")
    print(f"   总收益率: {results.get('performance', {}).get('total_return', 0):.2%}")
    print(f"   交易次数: {len(results.get('trades', []))}")
    
    # 分析交易记录
    trades = results.get('trades', [])
    buy_trades = [t for t in trades if t['action'] == 'BUY']
    sell_trades = [t for t in trades if t['action'] == 'SELL']
    
    print(f"   买入交易: {len(buy_trades)}")
    print(f"   卖出交易: {len(sell_trades)}")
    
    # 显示前几笔交易
    print("\n8. 前10笔交易记录:")
    for i, trade in enumerate(trades[:10]):
        action = trade['action']
        date = trade['date']
        price = trade['price']
        shares = trade['shares']
        position_size = trade.get('position_size', 'N/A')
        print(f"   {i+1}. {date} {action} {shares}股 @{price:.2f} 仓位:{position_size}")
    
    # 6. 验证分批建仓效果
    print("\n9. 分批建仓效果验证:")
    
    # 检查是否有多次买入
    if len(buy_trades) > 1:
        print("   ✓ 检测到多次买入交易，分批建仓功能正常")
        
        # 分析仓位变化
        position_sizes = [t.get('position_size', 0) for t in buy_trades]
        print(f"   买入仓位序列: {position_sizes}")
        
        # 检查是否有25%的仓位
        if 0.25 in position_sizes:
            print("   ✓ 检测到25%仓位建仓，符合策略设计")
        else:
            print("   ⚠ 未检测到25%仓位建仓")
            
    else:
        print("   ⚠ 只有一次买入交易，分批建仓可能未生效")
    
    # 检查仓位累积
    if len(buy_trades) >= 2:
        total_position = sum(t.get('position_size', 0) for t in buy_trades)
        print(f"   累计建仓比例: {total_position:.1%}")
        
        if total_position > 0.4:  # 至少两次25%建仓
            print("   ✓ 累计建仓比例合理，分批建仓成功")
        else:
            print("   ⚠ 累计建仓比例偏低")
    
    return results

if __name__ == "__main__":
    results = test_staged_position_building()
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)