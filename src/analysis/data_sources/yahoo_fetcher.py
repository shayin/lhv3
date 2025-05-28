"""
Yahoo Finance 数据抓取器

使用 yfinance 库抓取美股数据
"""

import pandas as pd
import yfinance as yf
from typing import List, Dict
import logging
from datetime import datetime, timedelta

from ..data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

class YahooDataFetcher(DataFetcher):
    """Yahoo Finance 数据抓取器"""
    
    def __init__(self, base_path: str = "data/raw"):
        super().__init__("yahoo", base_path)
        
        # 常用美股代码列表
        self.popular_stocks = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.'},
            {'symbol': 'META', 'name': 'Meta Platforms Inc.'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corporation'},
            {'symbol': 'NFLX', 'name': 'Netflix Inc.'},
            {'symbol': 'AMD', 'name': 'Advanced Micro Devices'},
            {'symbol': 'INTC', 'name': 'Intel Corporation'},
            {'symbol': 'CRM', 'name': 'Salesforce Inc.'},
            {'symbol': 'ORCL', 'name': 'Oracle Corporation'},
            {'symbol': 'ADBE', 'name': 'Adobe Inc.'},
            {'symbol': 'PYPL', 'name': 'PayPal Holdings Inc.'},
            {'symbol': 'UBER', 'name': 'Uber Technologies Inc.'},
            {'symbol': 'SPOT', 'name': 'Spotify Technology S.A.'},
            {'symbol': 'ZOOM', 'name': 'Zoom Video Communications'},
            {'symbol': 'SQ', 'name': 'Block Inc.'},
            {'symbol': 'SHOP', 'name': 'Shopify Inc.'},
            {'symbol': 'TWTR', 'name': 'Twitter Inc.'}
        ]
    
    def fetch_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        从Yahoo Finance抓取股票数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期，格式 YYYY-MM-DD
            end_date: 结束日期，格式 YYYY-MM-DD
            
        Returns:
            包含股票数据的DataFrame
        """
        try:
            # 设置默认日期范围（最近1年）
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            logger.info(f"从Yahoo Finance抓取数据: {symbol}, 日期范围: {start_date} 至 {end_date}")
            
            # 创建yfinance对象
            ticker = yf.Ticker(symbol)
            
            # 获取历史数据
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                logger.warning(f"Yahoo Finance未返回数据: {symbol}")
                return pd.DataFrame()
            
            # 重置索引，将日期从索引转为列
            hist.reset_index(inplace=True)
            
            # 标准化列名
            data = pd.DataFrame({
                'date': hist['Date'].dt.strftime('%Y-%m-%d'),
                'open': hist['Open'].round(2),
                'high': hist['High'].round(2),
                'low': hist['Low'].round(2),
                'close': hist['Close'].round(2),
                'volume': hist['Volume'].astype(int),
                'adj_close': hist['Close'].round(2)  # Yahoo Finance的Close已经是调整后价格
            })
            
            logger.info(f"成功获取数据: {symbol}, 行数: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"抓取Yahoo Finance数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> List[Dict[str, str]]:
        """
        获取常用美股列表
        
        Returns:
            股票列表
        """
        return self.popular_stocks.copy()
    
    def get_stock_info(self, symbol: str) -> Dict:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            股票信息字典
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', ''),
                'country': info.get('country', '')
            }
        except Exception as e:
            logger.error(f"获取股票信息失败: {symbol}, 错误: {e}")
            return {'symbol': symbol, 'name': '', 'error': str(e)}
    
    def search_stocks(self, query: str) -> List[Dict[str, str]]:
        """
        搜索股票（简单实现，基于预定义列表）
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的股票列表
        """
        query = query.upper()
        results = []
        
        for stock in self.popular_stocks:
            if query in stock['symbol'] or query in stock['name'].upper():
                results.append(stock)
        
        return results 