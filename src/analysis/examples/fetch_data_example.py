#!/usr/bin/env python3
"""
数据抓取示例脚本

演示如何使用数据抓取系统从不同数据源获取股票数据
"""

import sys
import os
# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

import logging
from datetime import datetime, timedelta

from src.analysis.data_manager import DataManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    print("=" * 80)
    print("数据抓取系统示例")
    print("=" * 80)
    
    # 初始化数据管理器
    # 如果有Tushare token，可以传入：DataManager(tushare_token="your_token")
    manager = DataManager()
    
    # 显示可用的数据源
    available_sources = manager.get_available_sources()
    print(f"可用数据源: {', '.join(available_sources)}")
    print()
    
    # 示例1: 从Yahoo Finance抓取美股数据
    if 'yahoo' in available_sources:
        print("示例1: 从Yahoo Finance抓取美股数据")
        print("-" * 50)
        
        # 抓取苹果公司股票数据
        symbol = "AAPL"
        start_date = "2024-01-01"
        end_date = "2024-12-31"
        
        print(f"抓取股票: {symbol}, 日期范围: {start_date} 至 {end_date}")
        file_path = manager.fetch_stock_data('yahoo', symbol, start_date, end_date)
        
        if file_path:
            print(f"✅ 数据已保存到: {file_path}")
        else:
            print("❌ 数据抓取失败")
        print()
    
    # 示例2: 批量抓取热门美股
    if 'yahoo' in available_sources:
        print("示例2: 批量抓取热门美股")
        print("-" * 50)
        
        # 获取热门股票列表
        popular_stocks = manager.get_stock_list('yahoo')
        symbols = [stock['symbol'] for stock in popular_stocks[:5]]  # 取前5只
        
        print(f"批量抓取股票: {', '.join(symbols)}")
        
        # 创建并执行任务
        task = manager.create_fetch_task('yahoo', symbols, start_date="2024-01-01")
        result = manager.execute_task(task)
        
        print(f"任务状态: {result['status']}")
        print(f"成功数量: {result['success_count']}/{result['total_symbols']}")
        print()
    
    # 示例3: 从AkShare抓取A股数据
    if 'akshare' in available_sources:
        print("示例3: 从AkShare抓取A股数据")
        print("-" * 50)
        
        # 抓取贵州茅台数据
        symbol = "600519"  # 贵州茅台
        print(f"抓取A股: {symbol}")
        
        file_path = manager.fetch_stock_data('akshare', symbol, start_date="2024-01-01")
        
        if file_path:
            print(f"✅ 数据已保存到: {file_path}")
        else:
            print("❌ 数据抓取失败")
        print()
    
    # 示例4: 搜索股票
    print("示例4: 搜索股票功能")
    print("-" * 50)
    
    for source in available_sources:
        print(f"在{source}中搜索'Apple':")
        results = manager.search_stocks(source, 'Apple')
        for stock in results[:3]:  # 显示前3个结果
            print(f"  - {stock['symbol']}: {stock['name']}")
        print()
    
    # 示例5: 按市场获取热门股票
    print("示例5: 按市场获取热门股票")
    print("-" * 50)
    
    popular_by_market = manager.get_popular_stocks_by_market()
    for market, stocks in popular_by_market.items():
        print(f"{market}热门股票:")
        for stock in stocks[:3]:  # 显示前3只
            print(f"  - {stock['symbol']}: {stock['name']}")
        print()
    
    print("=" * 80)
    print("示例完成！")
    print("数据已保存在 data/raw/ 目录下，按数据源和日期分类存储")
    print("=" * 80)

if __name__ == "__main__":
    main() 