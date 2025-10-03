#!/usr/bin/env python3
"""
调试分批建仓问题的脚本
验证回测引擎的买入条件限制问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from src.backend.strategy.enhanced_ma_strategy import EnhancedMAStrategy
from src.backend.backtest.engine import BacktestEngine
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_data():
    """创建测试数据，确保会产生分批建仓信号"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    
    # 创建一个明确的上升趋势，确保MA5会先上穿MA10，然后MA10上穿MA20
    base_price = 100
    prices = []
    
    for i in range(100):
        if i < 30:
            # 前30天：横盘，为MA计算提供基础
            price = base_price + np.random.normal(0, 1)
        elif i < 50:
            # 30-50天：缓慢上升，触发MA5上穿MA10
            price = base_price + (i - 30) * 0.5 + np.random.normal(0, 0.5)
        elif i < 80:
            # 50-80天：加速上升，触发MA10上穿MA20
            price = base_price + 10 + (i - 50) * 1.0 + np.random.normal(0, 0.5)
        else:
            # 80-100天：继续上升
            price = base_price + 40 + (i - 80) * 0.3 + np.random.normal(0, 0.5)
        
        prices.append(max(1, price))  # 确保价格为正
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': [1000000] * 100
    })
    data.set_index('date', inplace=True)
    
    return data

def test_strategy_signals():
    """测试策略信号生成"""
    logger.info("=== 测试策略信号生成 ===")
    
    # 创建测试数据
    data = create_test_data()
    
    # 创建策略实例
    strategy = EnhancedMAStrategy(
        name="测试增强MA策略",
        data=data,
        parameters={
            "n1": 5,
            "n2": 10, 
            "n3": 20,
            "position_per_stage": 0.25
        }
    )
    
    # 生成信号
    signals = strategy.generate_signals()
    
    # 分析信号
    buy_signals = signals[signals['signal'] == 1]
    sell_signals = signals[signals['signal'] == -1]
    
    logger.info(f"总买入信号数量: {len(buy_signals)}")
    logger.info(f"总卖出信号数量: {len(sell_signals)}")
    
    if len(buy_signals) > 0:
        logger.info("买入信号详情:")
        for idx, row in buy_signals.iterrows():
            logger.info(f"  日期: {idx}, 阶段: {row['stage']}, 仓位: {row['position_size']:.2%}, 原因: {row['trigger_reason']}")
    
    return signals

def test_backtest_engine():
    """测试回测引擎的买入逻辑"""
    logger.info("\n=== 测试回测引擎买入逻辑 ===")
    
    # 创建测试数据
    data = create_test_data()
    
    # 创建策略实例
    strategy = EnhancedMAStrategy(
        name="测试增强MA策略",
        data=data,
        parameters={
            "n1": 5,
            "n2": 10,
            "n3": 20,
            "position_per_stage": 0.25
        }
    )
    
    # 创建回测引擎
    engine = BacktestEngine(
        data=data,
        strategy=strategy,
        initial_capital=100000,
        commission_rate=0.001,
        slippage_rate=0.001
    )
    
    # 运行回测
    results = engine.run()
    
    # 分析结果
    trades = results.get('trades', [])
    buy_trades = [t for t in trades if t['action'] == 'BUY']
    sell_trades = [t for t in trades if t['action'] == 'SELL']
    
    logger.info(f"实际执行的买入交易数量: {len(buy_trades)}")
    logger.info(f"实际执行的卖出交易数量: {len(sell_trades)}")
    
    if buy_trades:
        logger.info("买入交易详情:")
        for i, trade in enumerate(buy_trades):
            logger.info(f"  交易{i+1}: 日期={trade['date']}, 仓位={trade.get('position_size', 'N/A'):.2%}, "
                       f"金额={trade['value']:.2f}, 原因={trade.get('trigger_reason', 'N/A')}")
    
    return results

def main():
    """主函数"""
    logger.info("开始调试分批建仓问题...")
    
    # 1. 测试策略信号生成
    signals = test_strategy_signals()
    
    # 2. 测试回测引擎执行
    results = test_backtest_engine()
    
    # 3. 对比分析
    logger.info("\n=== 问题分析 ===")
    buy_signals_count = len(signals[signals['signal'] == 1])
    actual_trades_count = len([t for t in results.get('trades', []) if t['action'] == 'BUY'])
    
    logger.info(f"策略生成的买入信号数量: {buy_signals_count}")
    logger.info(f"引擎实际执行的买入交易数量: {actual_trades_count}")
    
    if buy_signals_count > actual_trades_count:
        logger.error("❌ 确认问题：回测引擎没有执行所有的买入信号！")
        logger.error("   原因：引擎的买入条件 'self.position == 0' 阻止了分批建仓")
    else:
        logger.info("✅ 买入信号都被正确执行")

if __name__ == "__main__":
    main()