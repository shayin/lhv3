"""
美股数据抓取测试脚本

专门测试AkShare的美股数据抓取功能
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

def test_us_stocks():
    """测试美股数据抓取"""
    print("=== 美股数据抓取测试 ===\n")
    
    # 初始化数据管理器
    manager = DataManager()
    
    # 测试的美股列表
    us_stocks = [
        {'symbol': 'AAPL', 'name': '苹果公司'},
        {'symbol': 'TSLA', 'name': '特斯拉'},
        {'symbol': 'MSFT', 'name': '微软'},
        {'symbol': 'GOOGL', 'name': '谷歌'},
        {'symbol': 'BABA', 'name': '阿里巴巴'},
        {'symbol': 'JD', 'name': '京东'},
        {'symbol': 'NIO', 'name': '蔚来'},
        {'symbol': 'NVDA', 'name': '英伟达'}
    ]
    
    print(f"测试股票数量: {len(us_stocks)}")
    print("股票列表:")
    for stock in us_stocks:
        print(f"  - {stock['symbol']}: {stock['name']}")
    print()
    
    # 逐个测试
    success_count = 0
    failed_stocks = []
    
    for i, stock in enumerate(us_stocks, 1):
        symbol = stock['symbol']
        name = stock['name']
        
        print(f"[{i}/{len(us_stocks)}] 测试 {symbol} ({name})...")
        
        try:
            file_path = manager.fetch_stock_data('akshare', symbol, 
                                               start_date='2024-04-01', 
                                               end_date='2024-05-01')
            
            if file_path:
                print(f"  ✅ 成功: {file_path}")
                success_count += 1
                
                # 读取并显示数据摘要
                import pandas as pd
                data = pd.read_csv(file_path)
                print(f"  📊 数据行数: {len(data)}")
                print(f"  📅 日期范围: {data['date'].min()} 至 {data['date'].max()}")
                print(f"  💰 价格范围: ${data['low'].min():.2f} - ${data['high'].max():.2f}")
            else:
                print(f"  ❌ 失败: 未获取到数据")
                failed_stocks.append(stock)
                
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            failed_stocks.append(stock)
        
        print()
    
    # 测试结果汇总
    print("=== 测试结果汇总 ===")
    print(f"总测试数量: {len(us_stocks)}")
    print(f"成功数量: {success_count}")
    print(f"失败数量: {len(failed_stocks)}")
    print(f"成功率: {success_count/len(us_stocks)*100:.1f}%")
    
    if failed_stocks:
        print("\n失败的股票:")
        for stock in failed_stocks:
            print(f"  - {stock['symbol']}: {stock['name']}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_us_stocks() 