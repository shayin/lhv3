"""
数据抓取管理器

统一管理不同数据源的抓取工作
"""

import logging
from typing import Dict, List, Optional, Union
from datetime import datetime

from .data_sources.yahoo_fetcher import YahooDataFetcher
from .data_sources.akshare_fetcher import AkshareDataFetcher
from .data_sources.tushare_fetcher import TushareDataFetcher

logger = logging.getLogger(__name__)

class DataManager:
    """数据抓取管理器"""
    
    def __init__(self, tushare_token: Optional[str] = None, base_path: str = "data/raw"):
        """
        初始化数据管理器
        
        Args:
            tushare_token: Tushare API token
            base_path: 数据保存基础路径
        """
        self.base_path = base_path
        self.fetchers = {}
        
        # 初始化各种数据源
        try:
            self.fetchers['yahoo'] = YahooDataFetcher(base_path)
            logger.info("Yahoo Finance数据源已初始化")
        except Exception as e:
            logger.error(f"Yahoo Finance数据源初始化失败: {e}")
        
        try:
            self.fetchers['akshare'] = AkshareDataFetcher(base_path)
            logger.info("AkShare数据源已初始化")
        except Exception as e:
            logger.error(f"AkShare数据源初始化失败: {e}")
        
        try:
            self.fetchers['tushare'] = TushareDataFetcher(tushare_token, base_path)
            logger.info("Tushare数据源已初始化")
        except Exception as e:
            logger.error(f"Tushare数据源初始化失败: {e}")
    
    def get_available_sources(self) -> List[str]:
        """
        获取可用的数据源列表
        
        Returns:
            可用数据源名称列表
        """
        return list(self.fetchers.keys())
    
    def fetch_stock_data(self, source: str, symbol: str, start_date: str = None, end_date: str = None) -> Optional[str]:
        """
        从指定数据源抓取股票数据
        
        Args:
            source: 数据源名称 ('yahoo', 'akshare', 'tushare')
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            保存的文件路径，失败返回None
        """
        if source not in self.fetchers:
            logger.error(f"不支持的数据源: {source}")
            return None
        
        fetcher = self.fetchers[source]
        return fetcher.fetch_and_save(symbol, start_date, end_date)
    
    def batch_fetch(self, source: str, symbols: List[str], start_date: str = None, end_date: str = None) -> Dict[str, str]:
        """
        批量抓取数据
        
        Args:
            source: 数据源名称
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            抓取结果字典，键为股票代码，值为文件路径
        """
        if source not in self.fetchers:
            logger.error(f"不支持的数据源: {source}")
            return {}
        
        fetcher = self.fetchers[source]
        return fetcher.batch_fetch(symbols, start_date, end_date)
    
    def get_stock_list(self, source: str) -> List[Dict[str, str]]:
        """
        获取股票列表
        
        Args:
            source: 数据源名称
            
        Returns:
            股票列表
        """
        if source not in self.fetchers:
            logger.error(f"不支持的数据源: {source}")
            return []
        
        fetcher = self.fetchers[source]
        return fetcher.get_stock_list()
    
    def search_stocks(self, source: str, query: str) -> List[Dict[str, str]]:
        """
        搜索股票
        
        Args:
            source: 数据源名称
            query: 搜索关键词
            
        Returns:
            匹配的股票列表
        """
        if source not in self.fetchers:
            logger.error(f"不支持的数据源: {source}")
            return []
        
        fetcher = self.fetchers[source]
        return fetcher.search_stocks(query)
    
    def get_popular_stocks_by_market(self) -> Dict[str, List[Dict[str, str]]]:
        """
        按市场获取热门股票
        
        Returns:
            按市场分类的热门股票字典
        """
        result = {}
        
        if 'yahoo' in self.fetchers:
            result['美股'] = self.fetchers['yahoo'].get_stock_list()
        
        if 'akshare' in self.fetchers:
            result['A股'] = self.fetchers['akshare'].get_stock_list()
        
        if 'tushare' in self.fetchers:
            result['A股专业版'] = self.fetchers['tushare'].get_stock_list()
        
        return result
    
    def create_fetch_task(self, source: str, symbols: Union[str, List[str]], 
                         start_date: str = None, end_date: str = None) -> Dict:
        """
        创建数据抓取任务
        
        Args:
            source: 数据源名称
            symbols: 股票代码或代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            任务信息字典
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        task = {
            'id': f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'source': source,
            'symbols': symbols,
            'start_date': start_date,
            'end_date': end_date,
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        logger.info(f"创建抓取任务: {task['id']}, 数据源: {source}, 股票数量: {len(symbols)}")
        return task
    
    def execute_task(self, task: Dict) -> Dict:
        """
        执行抓取任务
        
        Args:
            task: 任务信息字典
            
        Returns:
            执行结果
        """
        task_id = task['id']
        source = task['source']
        symbols = task['symbols']
        start_date = task.get('start_date')
        end_date = task.get('end_date')
        
        logger.info(f"开始执行任务: {task_id}")
        
        try:
            results = self.batch_fetch(source, symbols, start_date, end_date)
            
            success_count = sum(1 for path in results.values() if path is not None)
            
            task_result = {
                'task_id': task_id,
                'status': 'completed',
                'total_symbols': len(symbols),
                'success_count': success_count,
                'failed_count': len(symbols) - success_count,
                'results': results,
                'completed_at': datetime.now().isoformat()
            }
            
            logger.info(f"任务完成: {task_id}, 成功: {success_count}/{len(symbols)}")
            return task_result
            
        except Exception as e:
            logger.error(f"任务执行失败: {task_id}, 错误: {e}")
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            } 