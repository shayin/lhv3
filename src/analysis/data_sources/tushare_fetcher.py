"""
Tushare 数据抓取器

使用 tushare 库抓取专业金融数据
需要注册并获取token: https://tushare.pro/
"""

import pandas as pd
import tushare as ts
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta

from ..data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

class TushareDataFetcher(DataFetcher):
    """Tushare 数据抓取器"""
    
    def __init__(self, token: Optional[str] = None, base_path: str = "data/raw"):
        super().__init__("tushare", base_path)
        
        # 设置token
        if token:
            ts.set_token(token)
            self.pro = ts.pro_api()
            logger.info("Tushare token已设置")
        else:
            self.pro = None
            logger.warning("未设置Tushare token，部分功能可能不可用")
        
        # 常用股票代码列表（Tushare格式：代码.交易所）
        self.popular_stocks = [
            {'symbol': '000001.SZ', 'name': '平安银行'},
            {'symbol': '000002.SZ', 'name': '万科A'},
            {'symbol': '000858.SZ', 'name': '五粮液'},
            {'symbol': '002415.SZ', 'name': '海康威视'},
            {'symbol': '002594.SZ', 'name': 'BYD'},
            {'symbol': '300059.SZ', 'name': '东方财富'},
            {'symbol': '300750.SZ', 'name': '宁德时代'},
            {'symbol': '600000.SH', 'name': '浦发银行'},
            {'symbol': '600036.SH', 'name': '招商银行'},
            {'symbol': '600519.SH', 'name': '贵州茅台'},
            {'symbol': '600887.SH', 'name': '伊利股份'},
            {'symbol': '002304.SZ', 'name': '洋河股份'},
            {'symbol': '000568.SZ', 'name': '泸州老窖'},
            {'symbol': '600276.SH', 'name': '恒瑞医药'},
            {'symbol': '000661.SZ', 'name': '长春高新'},
            {'symbol': '300015.SZ', 'name': '爱尔眼科'},
            {'symbol': '002142.SZ', 'name': '宁波银行'},
            {'symbol': '600031.SH', 'name': '三一重工'},
            {'symbol': '000725.SZ', 'name': '京东方A'},
            {'symbol': '600036.SH', 'name': '招商银行'}
        ]
    
    def fetch_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        从Tushare抓取股票数据
        
        Args:
            symbol: 股票代码（Tushare格式：000001.SZ）
            start_date: 开始日期，格式 YYYY-MM-DD
            end_date: 结束日期，格式 YYYY-MM-DD
            
        Returns:
            包含股票数据的DataFrame
        """
        if self.pro is None:
            logger.error("Tushare API未初始化，请设置token")
            return pd.DataFrame()
        
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
            
            logger.info(f"从Tushare抓取数据: {symbol}, 日期范围: {start_date} 至 {end_date}")
            
            # 获取股票历史数据
            df = self.pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
            
            if df.empty:
                logger.warning(f"Tushare未返回数据: {symbol}")
                return pd.DataFrame()
            
            # 按日期排序
            df = df.sort_values('trade_date')
            
            # 标准化列名
            data = pd.DataFrame({
                'date': pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d'),
                'open': df['open'].round(2),
                'high': df['high'].round(2),
                'low': df['low'].round(2),
                'close': df['close'].round(2),
                'volume': df['vol'].astype(int) * 100,  # Tushare的成交量单位是手，转换为股
                'adj_close': df['close'].round(2)  # 暂时使用收盘价作为调整后价格
            })
            
            logger.info(f"成功获取数据: {symbol}, 行数: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"抓取Tushare数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> List[Dict[str, str]]:
        """
        获取常用股票列表
        
        Returns:
            股票列表
        """
        return self.popular_stocks.copy()
    
    def get_all_stocks(self) -> List[Dict[str, str]]:
        """
        获取所有股票列表
        
        Returns:
            所有股票列表
        """
        if self.pro is None:
            logger.error("Tushare API未初始化")
            return self.popular_stocks.copy()
        
        try:
            # 获取股票基本信息
            stock_basic = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
            
            stocks = []
            for _, row in stock_basic.iterrows():
                stocks.append({
                    'symbol': row['ts_code'],
                    'name': row['name'],
                    'industry': row['industry'],
                    'area': row['area'],
                    'list_date': row['list_date']
                })
            
            logger.info(f"获取股票列表成功: {len(stocks)}只股票")
            return stocks
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return self.popular_stocks.copy()
    
    def get_stock_info(self, symbol: str) -> Dict:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            股票信息字典
        """
        if self.pro is None:
            return {'symbol': symbol, 'name': '', 'error': 'API未初始化'}
        
        try:
            # 获取股票基本信息
            basic_info = self.pro.stock_basic(ts_code=symbol, fields='ts_code,symbol,name,area,industry,market,list_date')
            
            if basic_info.empty:
                return {'symbol': symbol, 'name': '', 'error': '未找到股票信息'}
            
            info = basic_info.iloc[0]
            
            return {
                'symbol': info['ts_code'],
                'name': info['name'],
                'industry': info['industry'],
                'area': info['area'],
                'market': info['market'],
                'list_date': info['list_date']
            }
            
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
        
        # 如果没有找到且API可用，从完整列表中搜索
        if not results and self.pro is not None:
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
    
    def get_daily_basic(self, symbol: str, trade_date: str = None) -> Dict:
        """
        获取股票每日基本面数据
        
        Args:
            symbol: 股票代码
            trade_date: 交易日期，格式YYYYMMDD
            
        Returns:
            基本面数据字典
        """
        if self.pro is None:
            return {'error': 'API未初始化'}
        
        try:
            if trade_date is None:
                trade_date = datetime.now().strftime('%Y%m%d')
            
            df = self.pro.daily_basic(ts_code=symbol, trade_date=trade_date,
                                    fields='ts_code,trade_date,turnover_rate,volume_ratio,pe,pb')
            
            if df.empty:
                return {'error': '未找到数据'}
            
            data = df.iloc[0]
            return {
                'symbol': data['ts_code'],
                'trade_date': data['trade_date'],
                'turnover_rate': data['turnover_rate'],
                'volume_ratio': data['volume_ratio'],
                'pe': data['pe'],
                'pb': data['pb']
            }
            
        except Exception as e:
            logger.error(f"获取基本面数据失败: {symbol}, 错误: {e}")
            return {'error': str(e)} 