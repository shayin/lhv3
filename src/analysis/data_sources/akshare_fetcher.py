"""
AkShare 数据抓取器

使用 akshare 库抓取A股数据
"""

import pandas as pd
import akshare as ak
from typing import List, Dict
import logging
from datetime import datetime, timedelta

from ..data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

class AkshareDataFetcher(DataFetcher):
    """AkShare 数据抓取器"""
    
    def __init__(self, base_path: str = "data/raw"):
        super().__init__("akshare", base_path)
        
        # 常用A股代码列表
        self.popular_stocks = [
            {'symbol': '000001', 'name': '平安银行'},
            {'symbol': '000002', 'name': '万科A'},
            {'symbol': '000858', 'name': '五粮液'},
            {'symbol': '002415', 'name': '海康威视'},
            {'symbol': '002594', 'name': 'BYD'},
            {'symbol': '300059', 'name': '东方财富'},
            {'symbol': '300750', 'name': '宁德时代'},
            {'symbol': '600000', 'name': '浦发银行'},
            {'symbol': '600036', 'name': '招商银行'},
            {'symbol': '600519', 'name': '贵州茅台'},
            {'symbol': '600887', 'name': '伊利股份'},
            {'symbol': '000858', 'name': '五粮液'},
            {'symbol': '002304', 'name': '洋河股份'},
            {'symbol': '000568', 'name': '泸州老窖'},
            {'symbol': '600276', 'name': '恒瑞医药'},
            {'symbol': '000661', 'name': '长春高新'},
            {'symbol': '300015', 'name': '爱尔眼科'},
            {'symbol': '002142', 'name': '宁波银行'},
            {'symbol': '600031', 'name': '三一重工'},
            {'symbol': '000725', 'name': '京东方A'}
        ]
    
    def fetch_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        从AkShare抓取股票数据
        
        Args:
            symbol: 股票代码（6位数字）
            start_date: 开始日期，格式 YYYY-MM-DD
            end_date: 结束日期，格式 YYYY-MM-DD
            
        Returns:
            包含股票数据的DataFrame
        """
        try:
            # 设置默认日期范围（最近1年）
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            else:
                end_date = end_date.replace('-', '')
                
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            else:
                start_date = start_date.replace('-', '')
            
            logger.info(f"从AkShare抓取数据: {symbol}, 日期范围: {start_date} 至 {end_date}")
            
            # 获取股票历史数据
            # akshare的股票历史数据接口
            stock_data = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                          start_date=start_date, end_date=end_date, adjust="")
            
            if stock_data.empty:
                logger.warning(f"AkShare未返回数据: {symbol}")
                return pd.DataFrame()
            
            # 标准化列名
            data = pd.DataFrame({
                'date': pd.to_datetime(stock_data['日期']).dt.strftime('%Y-%m-%d'),
                'open': stock_data['开盘'].round(2),
                'high': stock_data['最高'].round(2),
                'low': stock_data['最低'].round(2),
                'close': stock_data['收盘'].round(2),
                'volume': stock_data['成交量'].astype(int),
                'adj_close': stock_data['收盘'].round(2)  # 暂时使用收盘价作为调整后价格
            })
            
            logger.info(f"成功获取数据: {symbol}, 行数: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"抓取AkShare数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> List[Dict[str, str]]:
        """
        获取常用A股列表
        
        Returns:
            股票列表
        """
        return self.popular_stocks.copy()
    
    def get_all_stocks(self) -> List[Dict[str, str]]:
        """
        获取所有A股列表
        
        Returns:
            所有A股列表
        """
        try:
            # 获取A股股票列表
            stock_list = ak.stock_info_a_code_name()
            
            stocks = []
            for _, row in stock_list.iterrows():
                stocks.append({
                    'symbol': row['code'],
                    'name': row['name']
                })
            
            logger.info(f"获取A股列表成功: {len(stocks)}只股票")
            return stocks
            
        except Exception as e:
            logger.error(f"获取A股列表失败: {e}")
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
            # 获取股票基本信息
            info = ak.stock_individual_info_em(symbol=symbol)
            
            result = {'symbol': symbol}
            
            # 解析信息
            for _, row in info.iterrows():
                key = row['item']
                value = row['value']
                
                if key == '股票简称':
                    result['name'] = value
                elif key == '所属行业':
                    result['industry'] = value
                elif key == '总市值':
                    result['market_cap'] = value
                elif key == '流通市值':
                    result['float_market_cap'] = value
            
            return result
            
        except Exception as e:
            logger.error(f"获取股票信息失败: {symbol}, 错误: {e}")
            return {'symbol': symbol, 'name': '', 'error': str(e)}
    
    def search_stocks(self, query: str) -> List[Dict[str, str]]:
        """
        搜索股票
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的股票列表
        """
        results = []
        
        # 先在常用股票中搜索
        for stock in self.popular_stocks:
            if query in stock['symbol'] or query in stock['name']:
                results.append(stock)
        
        # 如果没有找到，尝试从完整列表中搜索
        if not results:
            try:
                all_stocks = self.get_all_stocks()
                for stock in all_stocks:
                    if query in stock['symbol'] or query in stock['name']:
                        results.append(stock)
                        if len(results) >= 20:  # 限制返回数量
                            break
            except Exception as e:
                logger.error(f"搜索股票失败: {e}")
        
        return results 