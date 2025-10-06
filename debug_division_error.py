#!/usr/bin/env python3
"""
详细的除零错误调试脚本
用于追踪extremum_strategy_v6中的除零错误位置
"""

import sys
import os
import traceback
import warnings
import numpy as np
import pandas as pd

# 添加项目路径
sys.path.append('/Users/shayin/data1/htdocs/project/joy/lhv3/src')

# 设置警告为错误，这样可以捕获除零警告
warnings.filterwarnings('error', category=RuntimeWarning)

from backend.backtest.engine import BacktestEngine
from backend.strategy.extremum_strategy_v6 import ExtremumStrategyV6

def debug_division_by_zero():
    """调试除零错误"""
    print("开始调试除零错误...")
    
    try:
        # 创建策略实例
        strategy = ExtremumStrategyV6()
        
        # 创建回测引擎
        engine = BacktestEngine(
            strategy=strategy,
            initial_capital=100000,
            commission_rate=0.001,
            slippage_rate=0.001
        )
        
        # 设置股票代码和时间范围
        symbol = "000001.SZ"
        start_date = "2023-01-01"
        end_date = "2023-12-31"
        
        print(f"开始回测 {symbol} 从 {start_date} 到 {end_date}")
        
        # 运行回测
        results = engine.run_backtest(symbol, start_date, end_date)
        
        print("回测成功完成！")
        print(f"结果: {results}")
        
    except ZeroDivisionError as e:
        print(f"捕获到除零错误: {e}")
        print("错误堆栈:")
        traceback.print_exc()
        
        # 获取详细的错误信息
        tb = traceback.extract_tb(e.__traceback__)
        for frame in tb:
            print(f"文件: {frame.filename}")
            print(f"行号: {frame.lineno}")
            print(f"函数: {frame.name}")
            print(f"代码: {frame.line}")
            print("-" * 50)
            
    except RuntimeWarning as e:
        print(f"捕获到运行时警告 (可能是除零): {e}")
        print("错误堆栈:")
        traceback.print_exc()
        
    except Exception as e:
        print(f"捕获到其他错误: {e}")
        print("错误类型:", type(e).__name__)
        print("错误堆栈:")
        traceback.print_exc()

def test_data_loading():
    """测试数据加载是否正常"""
    print("\n测试数据加载...")
    
    try:
        from backend.data.fetcher import DataFetcher
        
        fetcher = DataFetcher()
        symbol = "000001.SZ"
        start_date = "2023-01-01"
        end_date = "2023-12-31"
        
        data = fetcher.fetch_data(symbol, start_date, end_date, data_source="akshare")
        
        if data is None or data.empty:
            print("数据为空！")
            return False
            
        print(f"数据形状: {data.shape}")
        print(f"数据列: {data.columns.tolist()}")
        print(f"数据前5行:")
        print(data.head())
        
        # 检查是否有零值或NaN值
        print("\n检查零值和NaN值:")
        for col in data.columns:
            zero_count = (data[col] == 0).sum()
            nan_count = data[col].isna().sum()
            if zero_count > 0 or nan_count > 0:
                print(f"{col}: {zero_count} 个零值, {nan_count} 个NaN值")
                
        return True
        
    except Exception as e:
        print(f"数据加载失败: {e}")
        traceback.print_exc()
        return False

def test_strategy_indicators():
    """测试策略指标计算"""
    print("\n测试策略指标计算...")
    
    try:
        from backend.data.fetcher import DataFetcher
        from backend.strategy.extremum_strategy_v6 import ExtremumStrategyV6
        
        fetcher = DataFetcher()
        strategy = ExtremumStrategyV6()
        
        symbol = "000001.SZ"
        start_date = "2023-01-01"
        end_date = "2023-12-31"
        
        data = fetcher.fetch_data(symbol, start_date, end_date, data_source="akshare")
        
        if data is None or data.empty:
            print("无法加载数据")
            return False
            
        print("开始计算指标...")
        
        # 逐步计算指标，捕获每一步的错误
        try:
            # 计算移动平均
            data['ma_short'] = data['close'].rolling(window=5).mean()
            data['ma_long'] = data['close'].rolling(window=20).mean()
            print("移动平均计算完成")
            
            # 计算成交量移动平均
            data['volume_ma'] = data['volume'].rolling(window=20).mean()
            print("成交量移动平均计算完成")
            
            # 计算成交量比率
            data['volume_ratio'] = data['volume'] / data['volume_ma'].replace(0, 1e-9)
            print("成交量比率计算完成")
            
            # 计算价格变化百分比
            data['price_change_pct'] = data['close'].pct_change()
            print("价格变化百分比计算完成")
            
            # 检查计算结果
            print("\n指标统计:")
            for col in ['ma_short', 'ma_long', 'volume_ma', 'volume_ratio', 'price_change_pct']:
                if col in data.columns:
                    series = data[col]
                    print(f"{col}: min={series.min():.6f}, max={series.max():.6f}, "
                          f"零值={((series == 0).sum())}, NaN值={series.isna().sum()}, "
                          f"无穷值={np.isinf(series).sum()}")
                    
        except Exception as e:
            print(f"指标计算失败: {e}")
            traceback.print_exc()
            return False
            
        return True
        
    except Exception as e:
        print(f"策略指标测试失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("除零错误详细调试")
    print("=" * 60)
    
    # 1. 测试数据加载
    if not test_data_loading():
        print("数据加载测试失败，退出")
        sys.exit(1)
    
    # 2. 测试策略指标计算
    if not test_strategy_indicators():
        print("策略指标测试失败，退出")
        sys.exit(1)
    
    # 3. 运行完整的回测调试
    debug_division_by_zero()
    
    print("\n调试完成")