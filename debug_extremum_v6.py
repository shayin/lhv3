#!/usr/bin/env python3
"""
极大极小值策略v6除零错误调试脚本
直接调用策略生成信号，捕获除零错误
"""

import sys
import os
import warnings
import traceback
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from backend.strategy.extremum_strategy_v6 import ExtremumStrategyV6

# 将警告转换为错误，以便捕获除零警告
warnings.filterwarnings('error', category=RuntimeWarning)

def create_test_data():
    """创建测试数据，包含可能触发除零错误的边界条件"""
    print("创建测试数据...")
    
    # 创建100天的测试数据
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    # 基础价格数据
    base_price = 100.0
    prices = []
    volumes = []
    
    for i in range(100):
        # 创建一些特殊情况
        if i < 10:
            # 前10天价格相同（可能导致pct_change为0）
            price = base_price
            volume = 1000000
        elif i < 20:
            # 接下来10天价格为0（极端情况）
            price = 0.0001  # 接近0但不为0
            volume = 100
        elif i < 30:
            # 成交量为0的情况
            price = base_price + (i - 20) * 0.1
            volume = 0
        elif i < 50:
            # 正常波动
            price = base_price + np.sin(i * 0.1) * 10
            volume = 1000000 + np.random.randint(-100000, 100000)
        else:
            # 极端波动
            if i % 10 == 0:
                price = base_price * 2  # 价格翻倍
            elif i % 10 == 5:
                price = base_price * 0.5  # 价格减半
            else:
                price = base_price + np.random.normal(0, 5)
            volume = max(100, 1000000 + np.random.randint(-500000, 500000))
        
        prices.append(price)
        volumes.append(volume)
    
    # 创建OHLC数据
    data = pd.DataFrame({
        'date': dates,
        'open': [p * (1 + np.random.uniform(-0.01, 0.01)) for p in prices],
        'high': [p * (1 + abs(np.random.uniform(0, 0.02))) for p in prices],
        'low': [p * (1 - abs(np.random.uniform(0, 0.02))) for p in prices],
        'close': prices,
        'volume': volumes
    })
    
    # 确保high >= low >= 0
    data['high'] = np.maximum(data['high'], data['close'])
    data['low'] = np.minimum(data['low'], data['close'])
    data['high'] = np.maximum(data['high'], data['low'])
    
    print(f"测试数据创建完成，共{len(data)}行")
    print(f"价格范围: {data['close'].min():.4f} - {data['close'].max():.4f}")
    print(f"成交量范围: {data['volume'].min()} - {data['volume'].max()}")
    print(f"零成交量天数: {(data['volume'] == 0).sum()}")
    print(f"接近零价格天数: {(data['close'] < 0.01).sum()}")
    
    return data

def test_strategy_signals():
    """测试策略信号生成，捕获除零错误"""
    print("\n" + "="*50)
    print("测试极大极小值策略v6信号生成")
    print("="*50)
    
    try:
        # 创建测试数据
        test_data = create_test_data()
        
        # 设置测试参数
        test_parameters = {
            "lookback_period": 5,
            "extremum_confirm_days": 2,
            "min_price_change_pct": 0.02,
            "ma_short": 5,
            "ma_long": 10,
            "volume_ma_period": 10,
            "rsi_period": 14,
            "signal_strength_threshold": 0.5,
            "max_position_ratio": 0.8,
            "base_position_size": 0.2,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10,
            "trailing_stop_pct": 0.03
        }
        
        # 创建策略实例，直接传入参数
        strategy = ExtremumStrategyV6(parameters=test_parameters)
        strategy.set_data(test_data)
        
        print("开始生成信号...")
        
        # 生成信号
        signals = strategy.generate_signals()
        
        print(f"信号生成成功！")
        print(f"数据行数: {len(signals)}")
        print(f"买入信号数: {(signals['signal'] == 1).sum()}")
        print(f"卖出信号数: {(signals['signal'] == -1).sum()}")
        
        # 检查是否有异常值
        print("\n检查异常值:")
        for col in ['signal_strength', 'position_size']:
            if col in signals.columns:
                col_data = signals[col]
                print(f"{col}: min={col_data.min():.4f}, max={col_data.max():.4f}, "
                      f"NaN数量={col_data.isna().sum()}, inf数量={np.isinf(col_data).sum()}")
        
        # 显示一些信号详情
        signal_rows = signals[signals['signal'] != 0]
        if len(signal_rows) > 0:
            print(f"\n前5个交易信号:")
            print(signal_rows[['date', 'close', 'signal', 'signal_strength', 'trigger_reason']].head())
        
        return True
        
    except ZeroDivisionError as e:
        print(f"❌ 捕获到除零错误: {e}")
        print("错误位置:")
        traceback.print_exc()
        return False
        
    except RuntimeWarning as e:
        print(f"❌ 捕获到运行时警告（可能是除零）: {e}")
        print("警告位置:")
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"❌ 捕获到其他错误: {e}")
        print("错误详情:")
        traceback.print_exc()
        return False

def test_individual_methods():
    """测试策略的各个方法，逐一排查除零错误"""
    print("\n" + "="*50)
    print("测试策略各个方法")
    print("="*50)
    
    try:
        # 创建测试数据
        test_data = create_test_data()
        
        # 创建策略实例
        test_parameters = {
            "lookback_period": 5,
            "extremum_confirm_days": 2,
            "min_price_change_pct": 0.02,
            "ma_short": 5,
            "ma_long": 10,
            "volume_ma_period": 10,
            "rsi_period": 14,
            "signal_strength_threshold": 0.5,
            "max_position_ratio": 0.8,
            "base_position_size": 0.2,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10,
            "trailing_stop_pct": 0.03
        }
        strategy = ExtremumStrategyV6(parameters=test_parameters)
        strategy.set_data(test_data)
        
        print("1. 测试calculate_indicators方法...")
        df_with_indicators = strategy.calculate_indicators()
        print("   ✅ calculate_indicators 成功")
        
        # 检查指标中的异常值
        for col in df_with_indicators.columns:
            if df_with_indicators[col].dtype in ['float64', 'int64']:
                col_data = df_with_indicators[col]
                inf_count = np.isinf(col_data).sum()
                nan_count = col_data.isna().sum()
                if inf_count > 0 or nan_count > 0:
                    print(f"   ⚠️  {col}: inf={inf_count}, nan={nan_count}")
        
        print("2. 测试identify_extremum_candidates方法...")
        for i in range(20, min(50, len(df_with_indicators))):
            minima, maxima = strategy.identify_extremum_candidates(df_with_indicators, i)
            if len(minima) > 0 or len(maxima) > 0:
                print(f"   第{i}天: 极小值候选={len(minima)}, 极大值候选={len(maxima)}")
        print("   ✅ identify_extremum_candidates 成功")
        
        print("3. 测试calculate_signal_strength方法...")
        for i in range(20, min(30, len(df_with_indicators))):
            minima, maxima = strategy.identify_extremum_candidates(df_with_indicators, i)
            for extremum_idx in minima[:2]:  # 只测试前2个
                strength = strategy.calculate_signal_strength(df_with_indicators, extremum_idx, 'min', i)
                print(f"   极小值{extremum_idx}在第{i}天的信号强度: {strength:.4f}")
            for extremum_idx in maxima[:2]:  # 只测试前2个
                strength = strategy.calculate_signal_strength(df_with_indicators, extremum_idx, 'max', i)
                print(f"   极大值{extremum_idx}在第{i}天的信号强度: {strength:.4f}")
        print("   ✅ calculate_signal_strength 成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 方法测试失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 极大极小值策略v6除零错误调试")
    print("="*60)
    
    # 测试策略信号生成
    signal_test_success = test_strategy_signals()
    
    # 测试各个方法
    method_test_success = test_individual_methods()
    
    print("\n" + "="*60)
    if signal_test_success and method_test_success:
        print("✅ 所有测试通过，未发现除零错误")
    else:
        print("❌ 测试发现问题，请检查上述错误信息")
    print("="*60)