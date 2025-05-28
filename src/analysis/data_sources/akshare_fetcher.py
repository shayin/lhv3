"""
AkShare 数据抓取器

使用 akshare 库抓取A股和美股数据
"""

import pandas as pd
import akshare as ak
from typing import List, Dict
import logging
from datetime import datetime, timedelta
import re

from ..data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

class AkshareDataFetcher(DataFetcher):
    """AkShare 数据抓取器，支持A股和美股"""
    
    def __init__(self, base_path: str = None):
        super().__init__("akshare", base_path)
        
        # 常用A股代码列表
        self.popular_a_stocks = [
            {'symbol': '000001', 'name': '平安银行', 'market': 'A'},
            {'symbol': '000002', 'name': '万科A', 'market': 'A'},
            {'symbol': '000858', 'name': '五粮液', 'market': 'A'},
            {'symbol': '002415', 'name': '海康威视', 'market': 'A'},
            {'symbol': '002594', 'name': 'BYD', 'market': 'A'},
            {'symbol': '300059', 'name': '东方财富', 'market': 'A'},
            {'symbol': '300750', 'name': '宁德时代', 'market': 'A'},
            {'symbol': '600000', 'name': '浦发银行', 'market': 'A'},
            {'symbol': '600036', 'name': '招商银行', 'market': 'A'},
            {'symbol': '600519', 'name': '贵州茅台', 'market': 'A'},
            {'symbol': '600887', 'name': '伊利股份', 'market': 'A'},
            {'symbol': '002304', 'name': '洋河股份', 'market': 'A'},
            {'symbol': '000568', 'name': '泸州老窖', 'market': 'A'},
            {'symbol': '600276', 'name': '恒瑞医药', 'market': 'A'},
            {'symbol': '000661', 'name': '长春高新', 'market': 'A'},
            {'symbol': '300015', 'name': '爱尔眼科', 'market': 'A'},
            {'symbol': '002142', 'name': '宁波银行', 'market': 'A'},
            {'symbol': '600031', 'name': '三一重工', 'market': 'A'},
            {'symbol': '000725', 'name': '京东方A', 'market': 'A'}
        ]
        
        # 常用美股代码列表
        self.popular_us_stocks = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'market': 'US'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'market': 'US'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'market': 'US'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'market': 'US'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'market': 'US'},
            {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'market': 'US'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'market': 'US'},
            {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'market': 'US'},
            {'symbol': 'BABA', 'name': 'Alibaba Group Holding Limited', 'market': 'US'},
            {'symbol': 'JD', 'name': 'JD.com Inc.', 'market': 'US'},
            {'symbol': 'PDD', 'name': 'PDD Holdings Inc.', 'market': 'US'},
            {'symbol': 'BIDU', 'name': 'Baidu Inc.', 'market': 'US'},
            {'symbol': 'NIO', 'name': 'NIO Inc.', 'market': 'US'},
            {'symbol': 'XPEV', 'name': 'XPeng Inc.', 'market': 'US'},
            {'symbol': 'LI', 'name': 'Li Auto Inc.', 'market': 'US'},
            {'symbol': 'BILI', 'name': 'Bilibili Inc.', 'market': 'US'},
            {'symbol': 'TME', 'name': 'Tencent Music Entertainment Group', 'market': 'US'},
            {'symbol': 'IQ', 'name': 'iQIYI Inc.', 'market': 'US'},
            {'symbol': 'WB', 'name': 'Weibo Corporation', 'market': 'US'},
            {'symbol': 'DIDI', 'name': 'DiDi Global Inc.', 'market': 'US'}
        ]
    
    def _is_us_stock(self, symbol: str) -> bool:
        """判断是否为美股代码"""
        # 美股代码通常是字母组成，A股是数字
        return bool(re.match(r'^[A-Z]+$', symbol.upper()))
    
    def fetch_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        从AkShare抓取股票数据（支持A股和美股）
        
        Args:
            symbol: 股票代码（A股：6位数字，美股：字母代码）
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
            
            # 判断是A股还是美股
            if self._is_us_stock(symbol):
                return self._fetch_us_stock_data(symbol, start_date, end_date)
            else:
                return self._fetch_a_stock_data(symbol, start_date, end_date)
                
        except Exception as e:
            logger.error(f"抓取AkShare数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()
    
    def _fetch_a_stock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """抓取A股数据"""
        try:
            # 获取A股历史数据
            stock_data = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                          start_date=start_date, end_date=end_date, adjust="")
            
            if stock_data.empty:
                logger.warning(f"AkShare未返回A股数据: {symbol}")
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
            
            logger.info(f"成功获取A股数据: {symbol}, 行数: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"抓取A股数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()
    
    def _fetch_us_stock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """抓取美股数据"""
        try:
            # 使用stock_us_daily接口获取美股历史数据
            stock_data = ak.stock_us_daily(symbol=symbol)
            
            if stock_data is None or stock_data.empty:
                logger.warning(f"AkShare未返回美股数据: {symbol}")
                return pd.DataFrame()
            
            # 转换日期格式进行过滤
            start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
            
            # 确保日期列是datetime格式
            stock_data['date'] = pd.to_datetime(stock_data['date'])
            
            # 过滤日期范围
            mask = (stock_data['date'] >= start_date_formatted) & (stock_data['date'] <= end_date_formatted)
            stock_data = stock_data[mask]
            
            if stock_data.empty:
                logger.warning(f"指定日期范围内无美股数据: {symbol}, {start_date_formatted} 至 {end_date_formatted}")
                return pd.DataFrame()
            
            # 标准化数据格式
            data = pd.DataFrame({
                'date': stock_data['date'].dt.strftime('%Y-%m-%d'),
                'open': stock_data['open'].round(2),
                'high': stock_data['high'].round(2),
                'low': stock_data['low'].round(2),
                'close': stock_data['close'].round(2),
                'volume': stock_data['volume'].astype(int),
                'adj_close': stock_data['close'].round(2)  # 使用收盘价作为调整后价格
            })
            
            logger.info(f"成功获取美股数据: {symbol}, 行数: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"抓取美股数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> List[Dict[str, str]]:
        """
        获取常用股票列表（A股+美股）
        
        Returns:
            股票列表
        """
        return self.popular_a_stocks.copy() + self.popular_us_stocks.copy()
    
    def get_a_stock_list(self) -> List[Dict[str, str]]:
        """
        获取常用A股列表
        
        Returns:
            A股列表
        """
        return self.popular_a_stocks.copy()
    
    def get_us_stock_list(self) -> List[Dict[str, str]]:
        """
        获取常用美股列表
        
        Returns:
            美股列表
        """
        return self.popular_us_stocks.copy()
    
    def get_all_stocks(self) -> List[Dict[str, str]]:
        """
        获取所有股票列表（A股+美股）
        
        Returns:
            所有股票列表
        """
        try:
            all_stocks = []
            
            # 获取A股列表
            try:
                a_stock_list = ak.stock_info_a_code_name()
                for _, row in a_stock_list.iterrows():
                    all_stocks.append({
                        'symbol': row['code'],
                        'name': row['name'],
                        'market': 'A'
                    })
                logger.info(f"获取A股列表成功: {len(a_stock_list)}只股票")
            except Exception as e:
                logger.error(f"获取A股列表失败: {e}")
                all_stocks.extend(self.popular_a_stocks)
            
            # 获取美股列表
            try:
                us_stock_list = ak.stock_us_spot_em()
                # 只取前1000只活跃美股，避免数据过多
                for _, row in us_stock_list.head(1000).iterrows():
                    symbol = row.get('代码', row.get('symbol', ''))
                    name = row.get('名称', row.get('name', ''))
                    if symbol and name:
                        all_stocks.append({
                            'symbol': symbol,
                            'name': name,
                            'market': 'US'
                        })
                logger.info(f"获取美股列表成功: 1000只股票")
            except Exception as e:
                logger.error(f"获取美股列表失败: {e}")
                all_stocks.extend(self.popular_us_stocks)
            
            logger.info(f"获取股票列表成功: 总计{len(all_stocks)}只股票")
            return all_stocks
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return self.get_stock_list()
    
    def get_stock_info(self, symbol: str) -> Dict:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            股票信息字典
        """
        try:
            result = {'symbol': symbol}
            
            if self._is_us_stock(symbol):
                # 美股信息获取
                try:
                    # 尝试获取美股基本信息
                    info = ak.stock_us_fundamental(symbol=symbol)
                    if not info.empty:
                        result['name'] = info.get('公司名称', symbol)
                        result['market'] = 'US'
                        result['industry'] = info.get('行业', '')
                        result['market_cap'] = info.get('市值', '')
                except Exception as e:
                    logger.warning(f"获取美股详细信息失败: {symbol}, {e}")
                    # 从常用列表中查找
                    for stock in self.popular_us_stocks:
                        if stock['symbol'] == symbol:
                            result.update(stock)
                            break
            else:
                # A股信息获取
                info = ak.stock_individual_info_em(symbol=symbol)
                result['market'] = 'A'
                
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
    
    def search_stocks(self, query: str, market: str = 'all') -> List[Dict[str, str]]:
        """
        搜索股票
        
        Args:
            query: 搜索关键词
            market: 市场类型 ('all', 'A', 'US')
            
        Returns:
            匹配的股票列表
        """
        results = []
        
        # 确定搜索范围
        if market == 'A':
            search_list = self.popular_a_stocks
        elif market == 'US':
            search_list = self.popular_us_stocks
        else:
            search_list = self.get_stock_list()
        
        # 在常用股票中搜索
        for stock in search_list:
            if query.upper() in stock['symbol'].upper() or query in stock['name']:
                results.append(stock)
        
        # 如果没有找到，尝试从完整列表中搜索
        if not results:
            try:
                all_stocks = self.get_all_stocks()
                for stock in all_stocks:
                    if market != 'all' and stock.get('market') != market:
                        continue
                    if query.upper() in stock['symbol'].upper() or query in stock['name']:
                        results.append(stock)
                        if len(results) >= 20:  # 限制返回数量
                            break
            except Exception as e:
                logger.error(f"搜索股票失败: {e}")
        
        return results 