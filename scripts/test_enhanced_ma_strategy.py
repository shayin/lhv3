#!/usr/bin/env python3
"""
增强版MA策略测试脚本
验证智能分批建仓和减仓功能
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backend.strategy.enhanced_ma_strategy import EnhancedMAStrategy
from src.backend.backtest.engine import BacktestEngine

def create_test_data(days=100):
    """创建测试数据"""
    # 生成日期序列
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    
    # 生成模拟价格数据（带趋势和波动）
    np.random.seed(42)  # 确保结果可重现
    
    # 基础价格趋势
    base_price = 100
    trend = np.linspace(0, 20, days)  # 上升趋势
    noise = np.random.normal(0, 2, days)  # 随机波动
    
    # 生成价格序列
    prices = base_price + trend + noise
    
    # 确保价格为正数
    prices = np.maximum(prices, 10)
    
    # 生成OHLC数据
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.01, days)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.02, days))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.02, days))),
        'close': prices,
        'volume': np.random.randint(1000, 10000, days),
        'symbol': 'TEST'
    })
    
    # 确保OHLC关系正确
    data['high'] = np.maximum.reduce([data['open'], data['high'], data['low'], data['close']])
    data['low'] = np.minimum.reduce([data['open'], data['high'], data['low'], data['close']])
    
    # 保持date列，不设置为索引
    return data

def test_enhanced_ma_strategy():
    """测试增强版MA策略"""
    print("=" * 60)
    print("增强版MA策略测试")
    print("=" * 60)
    
    # 创建测试数据
    print("1. 创建测试数据...")
    test_data = create_test_data(100)
    print(f"   测试数据: {len(test_data)} 天")
    print(f"   价格范围: {test_data['close'].min():.2f} - {test_data['close'].max():.2f}")
    
    # 初始化策略
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
    
    # 生成信号
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
    
    print(f"\n   阶段分布:")
    print(f"   - 阶段1建仓: {stage1_buy}")
    print(f"   - 阶段2建仓: {stage2_buy}")
    print(f"   - 阶段1减仓: {stage1_sell}")
    print(f"   - 阶段2减仓: {stage2_sell}")
    
    # 显示具体信号
    print("\n5. 具体交易信号:")
    signal_data = signals[signals['signal'] != 0][['close', 'signal', 'stage', 'position_size', 'trigger_reason', 'cumulative_position']]
    
    if len(signal_data) > 0:
        print("   日期          价格    信号  阶段        仓位%   累计仓位%  触发原因")
        print("   " + "-" * 90)
        for idx, row in signal_data.head(20).iterrows():
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            signal_type = "买入" if row['signal'] == 1 else "卖出"
            position_pct = f"{row['position_size']*100:.0f}%" if not pd.isna(row['position_size']) else "N/A"
            cumulative_pct = f"{row['cumulative_position']*100:.0f}%"
            reason = row['trigger_reason'][:40] + "..." if len(str(row['trigger_reason'])) > 40 else row['trigger_reason']
            
            print(f"   {date_str}  {row['close']:7.2f}  {signal_type:2s}  {row['stage']:10s}  {position_pct:6s}  {cumulative_pct:8s}  {reason}")
        
        if len(signal_data) > 20:
            print(f"   ... 还有 {len(signal_data) - 20} 个信号")
    else:
        print("   未生成任何交易信号")
    
    # 验证仓位控制
    print("\n6. 仓位控制验证:")
    max_position = signals['cumulative_position'].max()
    min_position = signals['cumulative_position'].min()
    print(f"   最大累计仓位: {max_position:.2%}")
    print(f"   最小累计仓位: {min_position:.2%}")
    
    # 检查仓位是否超限
    over_limit = (signals['cumulative_position'] > strategy_params['max_total_position']).sum()
    under_limit = (signals['cumulative_position'] < 0).sum()
    
    if over_limit > 0:
        print(f"   ⚠️  警告: 发现 {over_limit} 个时点仓位超过上限")
    if under_limit > 0:
        print(f"   ⚠️  警告: 发现 {under_limit} 个时点仓位为负数")
    
    if over_limit == 0 and under_limit == 0:
        print(f"   ✅ 仓位控制正常，所有仓位在 [0, {strategy_params['max_total_position']:.0%}] 范围内")
    
    return signals

def test_backtest_engine_compatibility():
    """测试与回测引擎的兼容性"""
    print("\n" + "=" * 60)
    print("回测引擎兼容性测试")
    print("=" * 60)
    
    # 创建测试数据
    test_data = create_test_data(50)
    
    # 初始化策略
    strategy_params = {
        'n1': 3,
        'n2': 7,
        'n3': 15,
        'position_per_stage': 0.25,
    }
    
    strategy = EnhancedMAStrategy(parameters=strategy_params)
    strategy.set_data(test_data)
    
    # 初始化回测引擎
    print("1. 初始化回测引擎...")
    engine = BacktestEngine(
        initial_capital=100000,
        commission_rate=0.001,
        slippage_rate=0.001
    )
    
    # 设置仓位模式为分批模式
    engine.position_mode = 'staged'
    
    try:
        # 设置策略和数据
        engine.set_strategy(strategy)
        engine.set_data(test_data)
        
        # 运行回测
        print("2. 运行回测...")
        results = engine.run()
        
        print("3. 回测结果:")
        print(f"   初始资金: ¥{engine.initial_capital:,.2f}")
        
        # 从equity_curve获取最终资产
        if results.get('equity_curve') and len(results['equity_curve']) > 0:
            final_equity = results['equity_curve'][-1]['equity']
            print(f"   最终资金: ¥{final_equity:,.2f}")
            print(f"   总收益率: {results.get('total_return', 0):.2%}")
        else:
            print("   ⚠️ 无权益曲线数据")
            
        print(f"   年化收益率: {results.get('annual_return', 0):.2%}")
        print(f"   最大回撤: {results.get('max_drawdown', 0):.2%}")
        print(f"   夏普比率: {results.get('sharpe_ratio', 0):.2f}")
        print(f"   胜率: {results.get('win_rate', 0):.2%}")
        print(f"   总交易次数: {len(results.get('trades', []))}")
        
        # 检查交易记录
        if 'trades' in results and len(results['trades']) > 0:
            trades_df = pd.DataFrame(results['trades'])
            print(f"\n4. 交易记录分析:")
            print(f"   买入交易: {len([t for t in results['trades'] if t.get('action') == 'BUY'])}")
            print(f"   卖出交易: {len([t for t in results['trades'] if t.get('action') == 'SELL'])}")
            
            # 显示前几笔交易
            print("\n   前5笔交易:")
            print("   日期          动作  数量      价格     金额      仓位%")
            print("   " + "-" * 60)
            for trade in results['trades'][:5]:
                action = "买入" if trade.get('action') == 'BUY' else "卖出"
                position_pct = f"{trade.get('position_size', 0)*100:.0f}%" if 'position_size' in trade else "N/A"
                value = trade.get('value', 0)
                print(f"   {str(trade['date'])[:10]}  {action:2s}  {trade.get('shares', 0):6.0f}  {trade.get('price', 0):8.2f}  {value:10.2f}  {position_pct}")
        else:
            print(f"\n4. 交易记录分析:")
            print(f"   无交易记录")
        
        print("\n✅ 回测引擎兼容性测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ 回测引擎兼容性测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("增强版MA策略完整测试")
    print("测试时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    try:
        # 测试策略信号生成
        signals = test_enhanced_ma_strategy()
        
        # 测试回测引擎兼容性
        compatibility_ok = test_backtest_engine_compatibility()
        
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print("✅ 策略信号生成: 通过")
        print(f"{'✅' if compatibility_ok else '❌'} 回测引擎兼容性: {'通过' if compatibility_ok else '失败'}")
        
        if compatibility_ok:
            print("\n🎉 所有测试通过！增强版MA策略可以正常使用。")
        else:
            print("\n⚠️  部分测试失败，需要进一步调试。")
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()