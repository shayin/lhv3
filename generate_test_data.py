#!/usr/bin/env python3
"""
生成更多测试数据来调试v8策略
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_test_data():
    """生成包含极值的测试数据"""
    
    # 生成60天的数据
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(60)]
    
    # 生成基础价格趋势
    base_price = 150.0
    prices = []
    volumes = []
    
    np.random.seed(42)  # 固定随机种子以便重现
    
    for i in range(60):
        # 创建一些明显的极值点
        if i == 10:  # 极小值
            price_change = -0.08  # 下跌8%
        elif i == 25:  # 极大值
            price_change = 0.12   # 上涨12%
        elif i == 40:  # 极小值
            price_change = -0.06  # 下跌6%
        elif i == 55:  # 极大值
            price_change = 0.10   # 上涨10%
        else:
            # 正常波动
            price_change = np.random.normal(0, 0.02)  # 2%标准差的正态分布
        
        if i == 0:
            close_price = base_price
        else:
            close_price = prices[-1]['close'] * (1 + price_change)
        
        # 生成OHLC数据
        daily_volatility = 0.015  # 1.5%日内波动
        high = close_price * (1 + np.random.uniform(0, daily_volatility))
        low = close_price * (1 - np.random.uniform(0, daily_volatility))
        open_price = low + (high - low) * np.random.uniform(0.2, 0.8)
        
        # 确保OHLC逻辑正确
        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)
        
        # 生成成交量（在极值点附近放大）
        base_volume = 1000000
        if i in [10, 25, 40, 55]:  # 极值点
            volume = base_volume * np.random.uniform(2.0, 3.0)
        else:
            volume = base_volume * np.random.uniform(0.8, 1.2)
        
        prices.append({
            'date': dates[i].strftime('%Y-%m-%d'),
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': int(volume),
            'adj_close': round(close_price, 2)
        })
    
    # 创建DataFrame
    df = pd.DataFrame(prices)
    
    # 保存到文件
    output_file = "/Users/shayin/data1/htdocs/project/joy/lhv3/data/demo/AAPL_extended.csv"
    df.to_csv(output_file, index=False)
    
    print(f"生成测试数据: {len(df)} 行")
    print(f"保存到: {output_file}")
    print(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
    
    # 显示极值点
    print("\n预期的极值点:")
    for i in [10, 25, 40, 55]:
        row = df.iloc[i]
        print(f"  第{i+1}天 ({row['date']}): {row['close']:.2f}")
    
    return df

if __name__ == "__main__":
    generate_test_data()