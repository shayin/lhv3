#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from datetime import datetime
import sys
import subprocess
import os
import time
import random
import requests
from requests.exceptions import RequestException
import numpy as np
import argparse

# 尝试导入yfinance，如果版本不是0.2.54则进行更新
try:
    import yfinance as yf
    print(f"当前yfinance版本：{yf.__version__}")
    if yf.__version__ != '0.2.54':
        print(f"当前yfinance版本：{yf.__version__}，将更新到0.2.54...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance==0.2.54", "--index-url", "http://mirrors.aliyun.com/pypi/simple/", "--trusted-host", "mirrors.aliyun.com"])
        # 强制重新加载yfinance
        import importlib
        importlib.reload(yf)
except ImportError:
    print("正在安装yfinance...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance==0.2.54", "--index-url", "http://mirrors.aliyun.com/pypi/simple/", "--trusted-host", "mirrors.aliyun.com"])
    import yfinance as yf

# 尝试导入pandas_datareader
try:
    import pandas_datareader as pdr
    print(f"当前pandas_datareader版本：{pdr.__version__}")
except ImportError:
    print("正在安装pandas_datareader...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas_datareader", "--index-url", "http://mirrors.aliyun.com/pypi/simple/", "--trusted-host", "mirrors.aliyun.com"])
    import pandas_datareader as pdr
    print(f"当前pandas_datareader版本：{pdr.__version__}")

# 尝试导入alpha_vantage API
try:
    from alpha_vantage.timeseries import TimeSeries
    print(f"已加载alpha_vantage模块")
except ImportError:
    print("正在安装alpha_vantage...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "alpha_vantage", "--index-url", "http://mirrors.aliyun.com/pypi/simple/", "--trusted-host", "mirrors.aliyun.com"])
    from alpha_vantage.timeseries import TimeSeries
    print(f"已加载alpha_vantage模块")

# 尝试导入matplotlib进行数据可视化
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    print("警告: 未安装matplotlib，将无法显示图表。可通过运行以下命令安装：")
    print("pip install matplotlib")
    HAS_MATPLOTLIB = False

# Alpha Vantage API密钥 - 请替换为您自己的密钥
# 可以在 https://www.alphavantage.co/support/#api-key 免费获取
ALPHA_VANTAGE_API_KEY = "YOUR_API_KEY"

# 自定义会话对象
def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    })
    return session

def random_sleep(min_seconds=1, max_seconds=5):
    """随机延时，避免被检测为机器人行为"""
    sleep_time = random.uniform(min_seconds, max_seconds)
    print(f"休息 {sleep_time:.2f} 秒...")
    time.sleep(sleep_time)

def get_stock_data(ticker, start_date, end_date, output_file, max_retries=3):
    """
    获取股票历史数据并保存为CSV文件
    
    参数:
        ticker (str): 股票代码
        start_date (str): 开始日期，格式为 'YYYY-MM-DD'
        end_date (str): 结束日期，格式为 'YYYY-MM-DD'
        output_file (str): 输出CSV文件的路径
        max_retries (int): 最大重试次数
    """
    for attempt in range(max_retries):
        try:
            # 确认真实版本
            print(f"yfinance版本: {yf.__version__}")
            print(f"尝试 #{attempt+1}: 获取 {ticker} 从 {start_date} 到 {end_date} 的历史数据...")
            
            # 创建自定义会话
            session = get_session()
            
            # 在第一次重试前等待较长时间
            if attempt > 0:
                wait_time = random.uniform(10, 20) * attempt
                print(f"第 {attempt+1} 次重试，等待 {wait_time:.2f} 秒...")
                time.sleep(wait_time)
            
            # 使用yfinance下载数据，传入会话对象
            data = yf.download(ticker, start=start_date, end=end_date, progress=True, session=session)
            
            # 检查数据是否为空
            if data.empty:
                print(f"未获取到 {ticker} 的数据")
                continue
            
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
            
        except Exception as e:
            print(f"尝试 #{attempt+1} 失败: {e}")
            if "Rate limited" in str(e) and attempt < max_retries - 1:
                print("遇到速率限制，将在短暂延迟后重试...")
                random_sleep(5, 15 * (attempt + 1))
            elif attempt < max_retries - 1:
                print(f"获取数据时发生错误，将重试: {e}")
                random_sleep(3, 10)
            else:
                print(f"所有尝试都失败了: {e}")
                return False

def try_alpha_vantage(ticker, start_date, end_date, output_file, max_retries=2):
    """
    使用Alpha Vantage API获取股票数据
    
    参数:
        ticker (str): 股票代码
        start_date (str): 开始日期，格式为 'YYYY-MM-DD'
        end_date (str): 结束日期，格式为 'YYYY-MM-DD'
        output_file (str): 输出CSV文件的路径
        max_retries (int): 最大重试次数
    """
    for attempt in range(max_retries):
        try:
            print(f"尝试 #{attempt+1}: 使用Alpha Vantage API获取 {ticker} 数据...")
            
            # 在不同尝试之间添加随机延迟
            if attempt > 0:
                wait_time = random.uniform(10, 20) * attempt
                print(f"等待 {wait_time:.2f} 秒后重试...")
                time.sleep(wait_time)
            
            # 创建TimeSeries对象
            ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
            
            # 获取日数据
            # 注意：Alpha Vantage免费API每分钟限制5次请求，每天限制500次请求
            data, meta_data = ts.get_daily(symbol=ticker, outputsize='full')
            
            # 检查数据是否为空
            if data.empty:
                print(f"Alpha Vantage未获取到 {ticker} 的数据")
                continue
            
            # 重命名列
            data.columns = ['open', 'high', 'low', 'close', 'volume']
            
            # 重置索引
            data = data.reset_index()
            data.rename(columns={'index': 'date'}, inplace=True)
            
            # 格式化日期
            data['date'] = pd.to_datetime(data['date']).dt.strftime('%Y-%m-%d')
            
            # 筛选日期范围
            data = data[(data['date'] >= start_date) & (data['date'] <= end_date)]
            
            # 检查日期筛选后是否为空
            if data.empty:
                print(f"筛选日期范围后未获取到 {ticker} 的数据")
                continue
            
            # 按日期升序排序 (Alpha Vantage返回的是降序)
            data = data.sort_values('date')
            
            # 保存为CSV
            data.to_csv(output_file, index=False)
            print(f"Alpha Vantage数据已保存到 {output_file}")
            print(f"共获取了 {len(data)} 条记录")
            
            # 显示前几行数据
            print("\n数据预览:")
            print(data.head())
            
            return True
            
        except Exception as e:
            print(f"Alpha Vantage尝试 #{attempt+1} 失败: {e}")
            if attempt < max_retries - 1:
                print(f"将重试...")
                random_sleep(15, 30)
            else:
                print(f"所有Alpha Vantage尝试均失败: {e}")
                return False

def try_pandas_datareader(ticker, start_date, end_date, output_file, max_retries=3):
    """
    使用pandas_datareader获取股票数据
    """
    for attempt in range(max_retries):
        try:
            print(f"尝试 #{attempt+1}: 使用pandas_datareader获取 {ticker} 数据...")
            
            # 在不同尝试之间添加随机延迟
            if attempt > 0:
                wait_time = random.uniform(10, 20) * attempt
                print(f"等待 {wait_time:.2f} 秒后重试...")
                time.sleep(wait_time)
            
            # 对于Yahoo, 需要调整美股代码，确保ticker符合Yahoo格式
            yahoo_ticker = ticker
            if not ticker.endswith('.US') and '.' not in ticker:
                yahoo_ticker = ticker
            
            # 使用pandas_datareader获取数据
            data = pdr.get_data_yahoo(yahoo_ticker, start=start_date, end=end_date)
            
            if data.empty:
                print(f"pandas_datareader未获取到 {ticker} 的数据")
                continue
            
            # 重置索引
            data = data.reset_index()
            
            # 格式化日期
            data['Date'] = data['Date'].dt.strftime('%Y-%m-%d')
            
            # 重命名列为小写
            data.columns = [col.lower() for col in data.columns]
            
            # 确保列名符合要求
            if 'adj close' in data.columns:
                data = data.drop(columns=['adj close'])
                
            # 重命名列
            column_mapping = {
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }
            data = data.rename(columns=column_mapping)
            
            # 检查是否有所有必要的列
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in data.columns:
                    print(f"缺少必要的列: {col}")
                    raise ValueError(f"数据缺少必要的列: {col}")
            
            # 只保留必要的列
            data = data[required_columns]
            
            # 按日期排序
            data = data.sort_values('date')
            
            # 删除重复的日期
            data = data.drop_duplicates(subset=['date'])
            
            # 保存为CSV
            data.to_csv(output_file, index=False)
            print(f"数据已使用pandas_datareader保存到 {output_file}")
            print(f"共获取了 {len(data)} 条记录")
            
            # 显示前几行数据
            print("\n数据预览:")
            print(data.head())
            
            return True
            
        except Exception as e:
            print(f"pandas_datareader尝试 #{attempt+1} 失败: {e}")
            if attempt < max_retries - 1:
                print(f"将重试...")
                random_sleep(5, 10 * (attempt + 1))
            else:
                print(f"所有pandas_datareader尝试均失败: {e}")
                return False

def try_alternate_method(ticker, start_date, end_date, output_file, max_retries=3):
    """
    尝试使用替代方法获取股票数据
    """
    for attempt in range(max_retries):
        try:
            print(f"尝试 #{attempt+1}: 使用替代方法获取 {ticker} 数据...")
            
            # 创建自定义会话
            session = get_session()
            
            # 在不同尝试之间添加随机延迟
            if attempt > 0:
                wait_time = random.uniform(15, 30) * attempt
                print(f"等待 {wait_time:.2f} 秒后重试...")
                time.sleep(wait_time)
            
            # 创建Ticker对象，传入会话对象
            stock = yf.Ticker(ticker, session=session)
            
            # 尝试更小的数据范围或分段下载
            # 将请求分成两部分
            mid_date = pd.to_datetime(start_date) + (pd.to_datetime(end_date) - pd.to_datetime(start_date)) / 2
            mid_date_str = mid_date.strftime('%Y-%m-%d')
            
            print(f"分段下载 - 第一部分: {start_date} 到 {mid_date_str}")
            data1 = stock.history(start=start_date, end=mid_date_str)
            
            # 添加延迟
            random_sleep(5, 10)
            
            print(f"分段下载 - 第二部分: {mid_date_str} 到 {end_date}")
            data2 = stock.history(start=mid_date_str, end=end_date)
            
            # 合并数据
            data = pd.concat([data1, data2])
            
            if data.empty:
                print(f"替代方法仍未获取到 {ticker} 的数据")
                continue
                
            # 重置索引，将Date列从索引变为普通列
            data = data.reset_index()
            
            # 格式化日期列为字符串 YYYY-MM-DD 格式
            data['Date'] = data['Date'].dt.strftime('%Y-%m-%d')
            
            # 重命名列名为小写，与回测系统要求匹配
            data.columns = [col.lower() for col in data.columns]
            if 'date' not in data.columns and 'index' in data.columns:
                data = data.rename(columns={'index': 'date'})
            if 'stock splits' in data.columns:
                data = data.drop(columns=['stock splits'])
            if 'dividends' in data.columns:
                data = data.drop(columns=['dividends'])
            if 'adj close' in data.columns:
                data = data.drop(columns=['adj close'])
            
            # 确保列名符合要求
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in data.columns:
                    print(f"缺少必要的列: {col}")
                    raise ValueError(f"数据缺少必要的列: {col}")
                    
            # 只保留必要的列
            data = data[required_columns]
            
            # 按日期升序排序
            data = data.sort_values('date')
            
            # 删除重复的日期
            data = data.drop_duplicates(subset=['date'])
            
            # 保存为CSV文件
            data.to_csv(output_file, index=False)
            print(f"数据已保存到 {output_file}")
            print(f"共获取了 {len(data)} 条记录")
            
            # 显示前几行数据
            print("\n数据预览:")
            print(data.head())
            
            return True
            
        except Exception as e:
            print(f"替代方法尝试 #{attempt+1} 失败: {e}")
            if "Rate limited" in str(e) and attempt < max_retries - 1:
                print("遇到速率限制，将在较长延迟后重试...")
                random_sleep(15, 30 * (attempt + 1))
            elif attempt < max_retries - 1:
                print(f"替代方法出错，将重试: {e}")
                random_sleep(10, 20)
            else:
                print(f"所有替代方法尝试均失败: {e}")
                return False

def try_direct_csv_download(ticker, output_file):
    """尝试直接从Yahoo Finance下载CSV"""
    try:
        print(f"尝试直接从Yahoo Finance下载{ticker}的CSV...")
        # 创建自定义会话
        session = get_session()
        
        # 构建Yahoo Finance CSV下载URL
        crumb = "YOUR_CRUMB"  # 需要从网页或其他请求中获取
        cookie = "YOUR_COOKIE"  # 需要从网页或其他请求中获取
        
        # 添加日期参数
        current_time = int(time.time())
        period1 = "0"  # 从最早
        period2 = str(current_time)  # 到现在
        
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={period1}&period2={period2}&interval=1d&events=history&crumb={crumb}"
        
        # 添加cookie
        session.headers.update({'Cookie': cookie})
        
        print(f"下载URL: {url}")
        r = session.get(url)
        
        if r.status_code == 200 and r.text and 'Date,Open' in r.text:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(r.text)
            
            # 读取CSV验证数据
            data = pd.read_csv(output_file)
            
            # 检查并重命名列
            data.columns = [col.lower() for col in data.columns]
            if 'date' not in data.columns and 'index' in data.columns:
                data = data.rename(columns={'index': 'date'})
                
            # 保存为CSV文件
            data.to_csv(output_file, index=False)
            print(f"数据已直接下载并保存到 {output_file}")
            print(f"共获取了 {len(data)} 条记录")
            
            # 显示前几行数据
            print("\n数据预览:")
            print(data.head())
            
            return True
    except Exception as e:
        print(f"直接下载CSV尝试失败: {e}")
        return False

def use_local_test_data(ticker, output_file, start_date=None, end_date=None):
    """
    当所有方法都失败时，生成测试数据
    该函数生成模拟真实股票的测试数据，包含趋势、季节性和随机波动成分
    
    参数:
        ticker (str): 股票代码，用于确定初始价格和波动模式
        output_file (str): 输出CSV文件的路径
        start_date (str): 可选，开始日期，格式为 'YYYY-MM-DD'
        end_date (str): 可选，结束日期，格式为 'YYYY-MM-DD'
    """
    try:
        print(f"所有下载方法均失败，生成测试数据用于开发...")
        
        # 如果未提供日期范围，使用默认值
        if not start_date:
            start_date = "2018-01-01"
        if not end_date:
            end_date = "2023-12-31"
            
        # 创建日期范围
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.date_range(start=start, end=end, freq='B')  # 'B'表示仅工作日
        
        # 生成初始价格 - 模拟不同股票的不同价格水平
        seed = sum(ord(c) for c in ticker) % 100  # 基于股票代码生成种子
        np.random.seed(seed)
        
        if ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]:
            # 科技股，高价格
            base_price = np.random.uniform(100, 300)
        elif ticker in ["JPM", "BAC", "C", "WFC", "GS"]:
            # 银行股，中等价格
            base_price = np.random.uniform(40, 100)
        elif ticker in ["F", "GM", "AAL", "UAL", "DAL"]:
            # 传统行业，低价格
            base_price = np.random.uniform(10, 40)
        else:
            # 其他股票，随机价格
            base_price = np.random.uniform(20, 200)
            
        # 重置随机种子以确保后续随机性
        np.random.seed(None)
        
        # 模拟价格时间序列参数
        n = len(dates)  # 数据点数量
        
        # 趋势组件 (长期趋势)
        # 不同阶段有不同趋势
        trend_changes = np.random.randint(3, 8)  # 趋势变化点的数量
        change_points = np.sort(np.random.choice(range(n), trend_changes, replace=False))
        
        # 为每个阶段生成不同的趋势斜率
        trends = [np.random.normal(0.0001, 0.0005) for _ in range(trend_changes+1)]
        
        # 季节性组件 (周期性波动)
        seasonality_period = 252  # 一年的交易日约252天
        seasonality_amplitude = base_price * 0.05  # 季节性振幅为基础价格的5%
        
        # 波动率组件 (随机波动)
        volatility_base = base_price * 0.015  # 基础波动率
        
        # 波动率集群效应 (高波动率时期)
        volatility_cluster_periods = np.random.randint(2, 5)  # 高波动率时期的数量
        cluster_points = np.sort(np.random.choice(range(n), volatility_cluster_periods, replace=False))
        cluster_lengths = [np.random.randint(10, 30) for _ in range(volatility_cluster_periods)]
        
        # 初始化价格数组
        close_prices = np.zeros(n)
        close_prices[0] = base_price
        
        # 通过模拟随机过程生成价格序列
        current_trend_idx = 0
        for i in range(1, n):
            # 确定当前趋势
            if current_trend_idx < len(change_points) and i >= change_points[current_trend_idx]:
                current_trend_idx += 1
                
            current_trend = trends[current_trend_idx]
            
            # 季节性成分
            seasonal_component = seasonality_amplitude * np.sin(2 * np.pi * i / seasonality_period)
            
            # 波动率
            in_cluster = False
            for j in range(volatility_cluster_periods):
                if i >= cluster_points[j] and i < cluster_points[j] + cluster_lengths[j]:
                    in_cluster = True
                    break
                    
            # 高波动率期间的波动增加
            if in_cluster:
                volatility = volatility_base * np.random.uniform(2.0, 3.5)
            else:
                volatility = volatility_base * np.random.uniform(0.5, 1.5)
                
            # 每日回报率 = 趋势 + 季节性 + 波动
            daily_return = current_trend + seasonal_component / close_prices[i-1] + np.random.normal(0, volatility) / close_prices[i-1]
            
            # 确保没有极端的每日变化 (限制在 -10% 到 +10% 之间)
            daily_return = np.clip(daily_return, -0.1, 0.1)
            
            # 计算新价格
            close_prices[i] = close_prices[i-1] * (1 + daily_return)
        
        # 生成其他价格数据 (开盘价，最高价，最低价)
        prices = []
        for i in range(n):
            close_price = close_prices[i]
            
            # 日内波动
            intraday_volatility = close_price * np.random.uniform(0.01, 0.04)
            
            # 确保高低价格合理
            high_price = close_price + intraday_volatility * np.random.uniform(0.2, 1.0)
            low_price = close_price - intraday_volatility * np.random.uniform(0.2, 1.0)
            
            # 确保开盘价在高低价之间
            open_weight = np.random.beta(2, 2)  # Beta分布使开盘价更可能接近中间值
            open_price = low_price + open_weight * (high_price - low_price)
            
            # 调整确保低价 <= 开盘/收盘 <= 高价
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            # 生成成交量，考虑价格变动和波动率
            price_change_pct = abs(close_price / close_prices[i-1] - 1) if i > 0 else 0
            volume_base = np.random.uniform(500000, 5000000)
            volume = int(volume_base * (1 + 10 * price_change_pct))
            
            # 在高波动率期间增加成交量
            if in_cluster:
                volume = int(volume * np.random.uniform(1.5, 3.0))
                
            # 随机增加一些交易量峰值
            if np.random.random() < 0.05:  # 5%概率有特殊高交易量日
                volume = int(volume * np.random.uniform(3.0, 10.0))
                
            prices.append([open_price, high_price, low_price, close_price, volume])
        
        # 创建DataFrame
        df = pd.DataFrame(prices, columns=['open', 'high', 'low', 'close', 'volume'])
        df['date'] = [d.strftime('%Y-%m-%d') for d in dates]
        
        # 重新排列列
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        
        # 保存CSV
        df.to_csv(output_file, index=False)
        print(f"测试数据已生成并保存到 {output_file}")
        print(f"共生成了 {len(df)} 条记录")
        
        # 显示前几行数据
        print("\n数据预览:")
        print(df.head())
        
        # 显示统计信息
        print("\n数据统计:")
        print(f"开盘价范围: {df['open'].min():.2f} - {df['open'].max():.2f}")
        print(f"收盘价范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
        print(f"成交量范围: {df['volume'].min()} - {df['volume'].max()}")
        print(f"平均日波动率: {(df['high'] / df['low'] - 1).mean() * 100:.2f}%")
        
        return True
    except Exception as e:
        print(f"生成测试数据失败: {e}")
        return False

def plot_stock_data(data, ticker, output_file=None):
    """
    绘制股票数据的K线图、成交量图和价格走势
    
    参数:
        data (DataFrame): 股票数据
        ticker (str): 股票代码
        output_file (str): 可选，图表保存路径
    """
    if not HAS_MATPLOTLIB:
        print("未安装matplotlib，无法生成图表")
        return False
        
    try:
        # 转换日期为datetime对象用于绘图
        data['date'] = pd.to_datetime(data['date'])
        
        # 创建图表
        fig = plt.figure(figsize=(16, 12))
        fig.suptitle(f'{ticker} 股票价格走势图', fontsize=16)
        
        # 价格子图占3行，成交量子图占1行
        gs = fig.add_gridspec(4, 1)
        
        # K线图
        ax1 = fig.add_subplot(gs[:3, 0])
        ax1.set_title('价格走势')
        ax1.set_ylabel('价格')
        
        # 绘制K线
        for i in range(len(data)):
            # 当天的数据
            row = data.iloc[i]
            date = mdates.date2num(row['date'])
            open_price, close_price = row['open'], row['close']
            high, low = row['high'], row['low']
            
            # 涨跌色选择
            color = 'green' if close_price >= open_price else 'red'
            
            # 绘制K线的矩形部分
            ax1.plot([date, date], [low, high], color=color)
            rect_height = max(0.05, abs(close_price - open_price))
            
            # 确保绿色（涨）时实心，红色（跌）时空心
            if close_price >= open_price:
                ax1.add_patch(plt.Rectangle((date-0.3, open_price), 0.6, rect_height, color=color, alpha=0.5))
            else:
                ax1.add_patch(plt.Rectangle((date-0.3, close_price), 0.6, rect_height, color=color, fill=False))
        
        # 添加移动平均线
        for window in [5, 20, 60]:
            data[f'ma{window}'] = data['close'].rolling(window=window).mean()
            ax1.plot(data['date'], data[f'ma{window}'], label=f'{window}日均线')
        
        # 添加图例
        ax1.legend()
        
        # 成交量子图
        ax2 = fig.add_subplot(gs[3, 0], sharex=ax1)
        ax2.set_title('成交量')
        ax2.set_ylabel('成交量')
        
        # 绘制成交量柱状图，根据涨跌颜色设置
        for i in range(len(data)):
            row = data.iloc[i]
            date = mdates.date2num(row['date'])
            color = 'green' if row['close'] >= row['open'] else 'red'
            ax2.bar(date, row['volume'], color=color, alpha=0.5, width=0.8)
        
        # 设置日期格式
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        plt.xticks(rotation=45)
        
        # 添加网格
        ax1.grid(True, alpha=0.3)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图表
        if output_file:
            plt.savefig(output_file)
            print(f"图表已保存至: {output_file}")
        
        # 显示图表
        plt.show()
        return True
        
    except Exception as e:
        print(f"生成图表时发生错误: {e}")
        return False

if __name__ == "__main__":
    # 通过命令行参数解析获取股票代码和日期范围
    parser = argparse.ArgumentParser(description='下载股票历史数据')
    parser.add_argument('--ticker', type=str, default="AAPL", help='股票代码 (默认: AAPL)')
    parser.add_argument('--start', type=str, default="2022-01-01", help='开始日期 YYYY-MM-DD (默认: 2022-01-01)')
    parser.add_argument('--end', type=str, default="2023-12-31", help='结束日期 YYYY-MM-DD (默认: 2023-12-31)')
    parser.add_argument('--api-key', type=str, help='Alpha Vantage API密钥 (可选)')
    parser.add_argument('--output', type=str, help='输出文件路径 (可选，默认自动生成)')
    parser.add_argument('--force-test-data', action='store_true', help='强制生成测试数据，跳过API调用')
    parser.add_argument('--retry-count', type=int, default=2, help='每个数据源的重试次数 (默认: 2)')
    parser.add_argument('--plot', action='store_true', help='生成并显示数据图表')
    parser.add_argument('--save-plot', type=str, help='保存图表到指定路径 (格式: png, jpg, pdf等)')
    parser.add_argument('--no-header', action='store_true', help='CSV输出不包含表头')
    
    args = parser.parse_args()
    
    # 股票代码
    ticker = args.ticker
    
    # 日期范围
    start_date = args.start
    end_date = args.end
    
    # 重试次数
    retry_count = args.retry_count
    
    # 如果提供了API密钥，则使用它
    if args.api_key:
        ALPHA_VANTAGE_API_KEY = args.api_key
    
    # 当前时间，用于生成输出文件名
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 输出文件名
    if args.output:
        output_file = args.output
    else:
        output_file = f"{ticker}_daily_{start_date}_to_{end_date}_{now}.csv"
    
    success = False
    
    # 是否强制生成测试数据
    if args.force_test_data:
        print("\n==== 强制生成测试数据 ====")
        success = use_local_test_data(ticker, output_file, start_date, end_date)
    else:
        # 尝试各种方法获取数据
        print("==== 方法 1: 使用 yfinance.download() ====")
        success = get_stock_data(ticker, start_date, end_date, output_file, max_retries=retry_count)
        
        # 如果第一种方法失败，尝试Alpha Vantage
        if not success:
            print("\n==== 方法 2: 使用 Alpha Vantage API 获取数据 ====")
            if ALPHA_VANTAGE_API_KEY == "YOUR_API_KEY":
                print("未提供Alpha Vantage API密钥，跳过此方法")
            else:
                success = try_alpha_vantage(ticker, start_date, end_date, output_file, max_retries=retry_count)
        
        # 如果第二种方法失败，尝试pandas_datareader
        if not success:
            print("\n==== 方法 3: 使用 pandas_datareader 获取数据 ====")
            success = try_pandas_datareader(ticker, start_date, end_date, output_file, max_retries=retry_count)
        
        # 如果第三种方法失败，尝试替代方法
        if not success:
            print("\n==== 方法 4: 使用 yfinance.Ticker.history() 分段下载 ====")
            success = try_alternate_method(ticker, start_date, end_date, output_file, max_retries=retry_count)
        
        # 如果前四种方法都失败，尝试直接下载CSV
        if not success:
            print("\n==== 方法 5: 尝试直接从Yahoo Finance下载CSV ====")
            success = try_direct_csv_download(ticker, output_file)
            
        # 如果所有网络方法都失败，生成测试数据
        if not success:
            print("\n==== 方法 6: 生成测试数据 ====")
            success = use_local_test_data(ticker, output_file, start_date, end_date)
    
    # 如果成功获取或生成了数据，处理输出选项
    if success:
        # 重新读取数据以确保一致性
        data = pd.read_csv(output_file)
        
        # 如果需要不包含表头的输出
        if args.no_header:
            print(f"生成不包含表头的CSV文件...")
            data.to_csv(output_file, index=False, header=False)
            print(f"已更新 {output_file}")
        
        # 如果需要绘制图表
        if args.plot or args.save_plot:
            # 确定图表输出路径
            plot_output = args.save_plot if args.save_plot else None
            
            print(f"\n==== 生成股票数据图表 ====")
            plot_stock_data(data, ticker, plot_output)
            
        print(f"\n数据处理完成，文件已保存至: {output_file}")
        
    else:
        print("\n所有方法都失败，无法获取或生成股票数据")
        sys.exit(1) 