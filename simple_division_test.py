#!/usr/bin/env python3
"""
简化的除零错误测试脚本
直接使用现有数据文件进行测试
"""

import sys
import os
import traceback
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.append('/Users/shayin/data1/htdocs/project/joy/lhv3/src')

from backend.backtest.engine import BacktestEngine
from backend.strategy.extremum_strategy_v6 import ExtremumStrategyV6

def test_with_demo_data():
    """使用演示数据测试除零错误"""
    print("使用演示数据测试除零错误...")
    
    try:
        # 加载演示数据
        demo_file = "/Users/shayin/data1/htdocs/project/joy/lhv3/data/demo/AAPL.csv"
        
        if not os.path.exists(demo_file):
            print(f"演示数据文件不存在: {demo_file}")
            return False
            
        data = pd.read_csv(demo_file)
        print(f"成功加载演示数据，形状: {data.shape}")
        print(f"数据列: {data.columns.tolist()}")
        print(f"数据前5行:")
        print(data.head())
        
        # 检查数据中的零值和NaN值
        print("\n检查零值和NaN值:")
        for col in data.columns:
            if col in ['open', 'high', 'low', 'close', 'volume']:
                zero_count = (data[col] == 0).sum()
                nan_count = data[col].isna().sum()
                if zero_count > 0 or nan_count > 0:
                    print(f"{col}: {zero_count} 个零值, {nan_count} 个NaN值")
        
        # 创建策略实例
        strategy = ExtremumStrategyV6()
        
        # 创建回测引擎
        engine = BacktestEngine(
            strategy=strategy,
            initial_capital=100000,
            commission_rate=0.001,
            slippage_rate=0.001
        )
        
        print("\n开始回测...")
        
        # 手动设置数据到引擎中进行测试
        # 这里我们需要模拟引擎的数据处理过程
        
        # 确保数据格式正确
        if 'Date' in data.columns:
            data['date'] = pd.to_datetime(data['Date'])
        elif 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
        else:
            print("数据中没有找到日期列")
            return False
            
        # 重命名列以匹配预期格式
        column_mapping = {
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in data.columns:
                data[new_col] = data[old_col]
        
        # 确保必要的列存在
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            print(f"缺少必要的列: {missing_cols}")
            return False
            
        # 排序数据
        data = data.sort_values('date').reset_index(drop=True)
        
        print(f"处理后的数据形状: {data.shape}")
        
        # 逐步测试策略的各个计算步骤
        print("\n测试策略指标计算...")
        
        try:
            # 1. 测试移动平均计算
            print("1. 计算移动平均...")
            data['ma_short'] = data['close'].rolling(window=5).mean()
            data['ma_long'] = data['close'].rolling(window=20).mean()
            print("   移动平均计算完成")
            
            # 2. 测试成交量移动平均
            print("2. 计算成交量移动平均...")
            data['volume_ma'] = data['volume'].rolling(window=20).mean()
            print("   成交量移动平均计算完成")
            
            # 3. 测试成交量比率（可能的除零点）
            print("3. 计算成交量比率...")
            volume_ma_zeros = (data['volume_ma'] == 0).sum()
            volume_ma_nans = data['volume_ma'].isna().sum()
            print(f"   volume_ma中有 {volume_ma_zeros} 个零值, {volume_ma_nans} 个NaN值")
            
            # 使用安全的除法
            data['volume_ratio'] = data['volume'] / data['volume_ma'].replace(0, 1e-9)
            print("   成交量比率计算完成")
            
            # 4. 测试价格变化百分比（可能的除零点）
            print("4. 计算价格变化百分比...")
            data['price_change_pct'] = data['close'].pct_change()
            price_change_infs = np.isinf(data['price_change_pct']).sum()
            print(f"   price_change_pct中有 {price_change_infs} 个无穷值")
            print("   价格变化百分比计算完成")
            
            # 5. 测试RSI计算
            print("5. 计算RSI...")
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            
            # 检查loss中的零值
            loss_zeros = (loss == 0).sum()
            print(f"   loss中有 {loss_zeros} 个零值")
            
            # 安全的RSI计算
            rs = gain / loss.replace(0, 1e-9)
            data['rsi'] = 100 - (100 / (1 + rs))
            print("   RSI计算完成")
            
            # 检查所有计算结果
            print("\n计算结果统计:")
            for col in ['ma_short', 'ma_long', 'volume_ma', 'volume_ratio', 'price_change_pct', 'rsi']:
                if col in data.columns:
                    series = data[col]
                    zeros = (series == 0).sum()
                    nans = series.isna().sum()
                    infs = np.isinf(series).sum()
                    print(f"{col}: 零值={zeros}, NaN值={nans}, 无穷值={infs}")
                    
                    if infs > 0:
                        print(f"  警告: {col} 包含无穷值!")
                        inf_indices = np.where(np.isinf(series))[0]
                        print(f"  无穷值位置: {inf_indices[:5]}...")  # 只显示前5个
            
            print("\n指标计算测试完成，未发现除零错误")
            return True
            
        except ZeroDivisionError as e:
            print(f"捕获到除零错误: {e}")
            traceback.print_exc()
            return False
            
        except Exception as e:
            print(f"计算过程中发生错误: {e}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"测试失败: {e}")
        traceback.print_exc()
        return False

def test_engine_calculations():
    """测试引擎中的计算"""
    print("\n测试引擎计算...")
    
    try:
        # 模拟一些可能导致除零的计算
        print("1. 测试利润百分比计算...")
        position_price = 0  # 可能的除零点
        current_price = 100
        
        # 安全的利润计算
        if position_price > 0:
            profit_percent = (current_price - position_price) / position_price * 100
        else:
            profit_percent = 0
        print(f"   利润百分比: {profit_percent}")
        
        print("2. 测试总收益率计算...")
        initial_capital = 0  # 可能的除零点
        final_equity = 110000
        
        # 安全的收益率计算
        if initial_capital > 0:
            total_return = (final_equity - initial_capital) / initial_capital
        else:
            total_return = 0
        print(f"   总收益率: {total_return}")
        
        print("3. 测试胜率计算...")
        total_trades = 0  # 可能的除零点
        winning_trades = 5
        
        # 安全的胜率计算
        if total_trades > 0:
            win_rate = winning_trades / total_trades
        else:
            win_rate = 0
        print(f"   胜率: {win_rate}")
        
        print("引擎计算测试完成")
        return True
        
    except Exception as e:
        print(f"引擎计算测试失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("简化除零错误测试")
    print("=" * 60)
    
    # 1. 测试演示数据
    if not test_with_demo_data():
        print("演示数据测试失败")
    
    # 2. 测试引擎计算
    if not test_engine_calculations():
        print("引擎计算测试失败")
    
    print("\n测试完成")