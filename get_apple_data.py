#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yfinance as yf
import pandas as pd
from datetime import datetime

def get_stock_data(ticker, start_date, end_date, output_file):
    """
    获取股票历史数据并保存为CSV文件
    
    参数:
        ticker (str): 股票代码
        start_date (str): 开始日期，格式为 'YYYY-MM-DD'
        end_date (str): 结束日期，格式为 'YYYY-MM-DD'
        output_file (str): 输出CSV文件的路径
    """
    print(f"正在获取 {ticker} 从 {start_date} 到 {end_date} 的历史数据...")
    
    # 使用yfinance下载数据
    data = yf.download(ticker, start=start_date, end=end_date, progress=True)
    
    # 检查数据是否为空
    if data.empty:
        print(f"未获取到 {ticker} 的数据")
        return False
    
    # 重置索引，将Date列从索引变为普通列
    data = data.reset_index()
    
    # 格式化日期列为字符串 YYYY-MM-DD 格式
    data['Date'] = data['Date'].dt.strftime('%Y-%m-%d')
    
    # 重命名列名为小写，与回测系统要求匹配
    data.columns = ['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
    
    # 删除不需要的adj_close列
    data = data.drop(columns=['adj_close'])
    
    # 按日期升序排序
    data = data.sort_values('date')
    
    # 保存为CSV文件
    data.to_csv(output_file, index=False)
    print(f"数据已保存到 {output_file}")
    print(f"共获取了 {len(data)} 条记录")
    
    # 显示前几行数据
    print("\n数据预览:")
    print(data.head())
    
    return True

if __name__ == "__main__":
    # 股票代码
    ticker = "AAPL"
    
    # 日期范围
    start_date = "2018-01-01"
    end_date = "2024-12-31"
    
    # 当前时间，用于生成输出文件名
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 输出文件名
    output_file = f"{ticker}_daily_{start_date}_to_{end_date}_{now}.csv"
    
    # 获取数据并保存
    get_stock_data(ticker, start_date, end_date, output_file) 