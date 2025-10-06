#!/usr/bin/env python3
"""
追踪除零错误的详细脚本
直接调用回测引擎并捕获错误堆栈
"""

import sys
import os
import traceback
import warnings
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.append('/Users/shayin/data1/htdocs/project/joy/lhv3/src')

# 设置警告为错误
warnings.filterwarnings('error', category=RuntimeWarning)

from backend.backtest.engine import BacktestEngine
from backend.strategy.extremum_strategy_v6 import ExtremumStrategyV6
from backend.data.fetcher import DataFetcher

def trace_division_error():
    """追踪除零错误"""
    print("开始追踪除零错误...")
    
    try:
        # 创建策略实例
        strategy = ExtremumStrategyV6()
        print("策略实例创建成功")
        
        # 创建回测引擎
        engine = BacktestEngine(
            strategy=strategy,
            initial_capital=100000,
            commission_rate=0.0015,
            slippage_rate=0.001
        )
        print("回测引擎创建成功")
        
        # 直接创建模拟数据进行测试（跳过网络获取）
        print("创建模拟数据进行测试...")
        
        # 使用TSLA数据（与测试脚本一致）
        symbol = "TSLA"
        start_date = "2018-10-06"
        end_date = "2019-01-06"  # 缩短时间范围
        
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 创建更真实的股价数据
        np.random.seed(42)  # 固定随机种子
        n_days = len(dates)
        
        # 生成价格走势
        base_price = 100
        price_changes = np.random.randn(n_days) * 0.02  # 2%的日波动
        prices = [base_price]
        for change in price_changes[1:]:
            prices.append(prices[-1] * (1 + change))
        
        data = pd.DataFrame({
            'date': dates,
            'close': prices,
        })
        
        # 生成开盘、最高、最低价
        data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
        data['high'] = np.maximum(data['open'], data['close']) * (1 + np.random.uniform(0, 0.03, n_days))
        data['low'] = np.minimum(data['open'], data['close']) * (1 - np.random.uniform(0, 0.03, n_days))
        data['volume'] = np.random.randint(1000000, 10000000, n_days)
        
        # 故意创建一些可能导致除零的情况
        print("故意创建一些边界情况...")
        
        # 在某些位置设置相同的价格（可能导致价格变化为0）
        data.loc[10:15, ['open', 'high', 'low', 'close']] = 100.0
        
        # 在某些位置设置很小的成交量
        data.loc[20:25, 'volume'] = 1
        
        # 创建一些连续相同价格的情况
        data.loc[30:35, 'close'] = data.loc[30, 'close']
        
        if data is None or data.empty:
            print("无法获取数据，退出")
            return False
            
        print(f"数据获取成功，形状: {data.shape}")
        print(f"数据列: {data.columns.tolist()}")
        
        # 检查数据中的零值
        print("\n检查数据中的零值:")
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in data.columns:
                zero_count = (data[col] == 0).sum()
                if zero_count > 0:
                    print(f"警告: {col} 列有 {zero_count} 个零值")
                    # 修复零值
                    if col == 'volume':
                        data.loc[data[col] == 0, col] = 1000
                    else:
                        # 对于价格，用前一个非零值填充
                        data[col] = data[col].replace(0, np.nan).fillna(method='ffill').fillna(100)
        
        print("数据预处理完成")
        
        # 设置引擎数据
        engine.set_data(data)
        print("数据设置到引擎成功")
        
        # 设置策略参数
        parameters = {
            "positionConfig": {
                "mode": "fixed",
                "defaultSize": 0.5
            }
        }
        engine.set_parameters(parameters)
        print("参数设置成功")
        
        print("\n开始运行回测...")
        
        # 运行回测
        results = engine.run()
        
        print("回测成功完成！")
        print(f"结果键: {list(results.keys())}")
        
        if 'performance' in results:
            perf = results['performance']
            print(f"性能指标: {list(perf.keys())}")
            for key, value in perf.items():
                print(f"  {key}: {value}")
        
        return True
        
    except ZeroDivisionError as e:
        print(f"\n❌ 捕获到除零错误: {e}")
        print("\n错误堆栈:")
        tb = traceback.extract_tb(e.__traceback__)
        
        for i, frame in enumerate(tb):
            print(f"\n堆栈 {i+1}:")
            print(f"  文件: {frame.filename}")
            print(f"  行号: {frame.lineno}")
            print(f"  函数: {frame.name}")
            print(f"  代码: {frame.line}")
            
            # 如果是我们的代码文件，显示更多上下文
            if 'lhv3/src' in frame.filename:
                print(f"  >>> 这是项目代码中的错误！")
                try:
                    with open(frame.filename, 'r') as f:
                        lines = f.readlines()
                        start = max(0, frame.lineno - 3)
                        end = min(len(lines), frame.lineno + 2)
                        print(f"  上下文代码 (行 {start+1}-{end}):")
                        for j in range(start, end):
                            marker = ">>> " if j == frame.lineno - 1 else "    "
                            print(f"  {marker}{j+1:3d}: {lines[j].rstrip()}")
                except:
                    pass
        
        return False
        
    except RuntimeWarning as e:
        print(f"\n⚠️ 捕获到运行时警告 (可能是除零): {e}")
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"\n❌ 捕获到其他错误: {e}")
        print(f"错误类型: {type(e).__name__}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("除零错误详细追踪")
    print("=" * 60)
    
    success = trace_division_error()
    
    if success:
        print("\n✅ 追踪完成，未发现除零错误")
    else:
        print("\n❌ 追踪完成，发现除零错误")
    
    print("\n追踪结束")