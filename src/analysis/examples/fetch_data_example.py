#!/usr/bin/env python3
"""
数据抓取示例脚本

演示如何使用数据抓取系统获取A股和美股数据
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.analysis.data_manager import DataManager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """主函数"""
    print("=== 数据抓取系统演示 ===\n")
    
    # 初始化数据管理器
    manager = DataManager()
    
    # 显示可用数据源
    print("1. 可用数据源:")
    sources = manager.get_available_sources()
    for source in sources:
        print(f"   - {source}")
    print()
    
    # 检查AkShare数据源是否可用
    if 'akshare' not in sources:
        print("AkShare数据源不可用")
        return
    
    print("2. AkShare数据源功能演示:")
    
    # 演示A股数据抓取
    print("\n--- A股数据抓取 ---")
    print("抓取贵州茅台(600519)数据...")
    a_stock_path = manager.fetch_stock_data('akshare', '600519', start_date='2020-04-01', end_date='2024-05-01')
    if a_stock_path:
        print(f"✅ A股数据已保存到: {a_stock_path}")
    else:
        print("❌ A股数据获取失败")
    
    # 演示美股数据抓取
    print("\n--- 美股数据抓取 ---")
    print("抓取苹果公司(AAPL)数据...")
    us_stock_path = manager.fetch_stock_data('akshare', 'AAPL', start_date='2020-01-01', end_date='2025-05-26')
    if us_stock_path:
        print(f"✅ 美股数据已保存到: {us_stock_path}")
    else:
        print("❌ 美股数据获取失败")
    
    # 演示中概股数据抓取
    print("\n--- 中概股数据抓取 ---")
    print("抓取阿里巴巴(BABA)数据...")
    baba_path = manager.fetch_stock_data('akshare', 'BABA', start_date='2024-04-01', end_date='2024-05-01')
    if baba_path:
        print(f"✅ 中概股数据已保存到: {baba_path}")
    else:
        print("❌ 中概股数据获取失败")
    
    # 演示特斯拉数据抓取
    print("\n--- 特斯拉数据抓取 ---")
    print("抓取特斯拉(TSLA)数据...")
    tsla_path = manager.fetch_stock_data('akshare', 'TSLA', start_date='2024-04-01', end_date='2024-05-01')
    if tsla_path:
        print(f"✅ 特斯拉数据已保存到: {tsla_path}")
    else:
        print("❌ 特斯拉数据获取失败")
    
    # 演示股票列表功能
    print("\n3. 股票列表功能演示:")
    stock_list = manager.get_stock_list('akshare')
    print(f"AkShare股票列表数量: {len(stock_list)}")
    
    # 显示A股股票
    a_stocks = [stock for stock in stock_list if stock.get('market') == 'A']
    print(f"\nA股常用股票 ({len(a_stocks)}只):")
    for stock in a_stocks[:5]:
        print(f"   {stock['symbol']} - {stock['name']}")
    
    # 显示美股股票
    us_stocks = [stock for stock in stock_list if stock.get('market') == 'US']
    print(f"\n美股常用股票 ({len(us_stocks)}只):")
    for stock in us_stocks[:5]:
        print(f"   {stock['symbol']} - {stock['name']}")
    
    # 演示搜索功能
    print("\n4. 股票搜索功能演示:")
    
    # 搜索茅台
    print("\n--- 搜索 '茅台' ---")
    search_results = manager.search_stocks('akshare', '茅台')
    for stock in search_results:
        market = stock.get('market', 'Unknown')
        print(f"   {stock['symbol']} - {stock['name']} ({market})")
    
    # 搜索Apple
    print("\n--- 搜索 'Apple' ---")
    search_results = manager.search_stocks('akshare', 'Apple')
    for stock in search_results:
        market = stock.get('market', 'Unknown')
        print(f"   {stock['symbol']} - {stock['name']} ({market})")
    
    # 搜索Tesla
    print("\n--- 搜索 'Tesla' ---")
    search_results = manager.search_stocks('akshare', 'Tesla')
    for stock in search_results:
        market = stock.get('market', 'Unknown')
        print(f"   {stock['symbol']} - {stock['name']} ({market})")
    
    # 演示批量抓取
    print("\n5. 批量数据抓取演示:")
    
    # 批量抓取多只股票（A股+美股）
    symbols = ['600519', 'AAPL', 'TSLA', '000858', 'MSFT']
    print(f"批量抓取股票: {symbols}")
    
    batch_results = manager.batch_fetch('akshare', symbols, start_date='2020-01-01', end_date='2025-05-26')
    
    print("批量抓取结果:")
    for symbol, file_path in batch_results.items():
        if file_path:
            print(f"   ✅ {symbol}: {file_path}")
        else:
            print(f"   ❌ {symbol}: 抓取失败")
    
    # 演示按市场分类的热门股票
    print("\n6. 按市场分类的热门股票:")
    popular_stocks = manager.get_popular_stocks_by_market()
    for market, stocks in popular_stocks.items():
        print(f"\n{market} ({len(stocks)}只):")
        for stock in stocks[:3]:  # 显示前3只
            print(f"   {stock['symbol']} - {stock['name']}")
    
    print("\n=== 演示完成 ===")
    print("数据已保存在 data/raw/akshare/ 目录下")

if __name__ == "__main__":
    main() 