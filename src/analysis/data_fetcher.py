"""
数据抓取基类

提供统一的数据抓取接口和文件保存功能
"""

import os
import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DataFetcher(ABC):
    """数据抓取基类"""
    
    def __init__(self, data_source_name: str, base_path: str = None):
        """
        初始化数据抓取器
        
        Args:
            data_source_name: 数据源名称，如 'yahoo', 'akshare', 'tushare' 等
            base_path: 数据保存的基础路径，如果为None则使用项目根目录下的data/raw
        """
        self.data_source_name = data_source_name
        
        # 如果没有指定base_path，使用项目根目录下的data/raw
        if base_path is None:
            # 获取项目根目录（从当前文件向上找到包含src目录的目录）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            while project_root != os.path.dirname(project_root):  # 避免无限循环
                if os.path.exists(os.path.join(project_root, 'src')):
                    break
                project_root = os.path.dirname(project_root)
            
            self.base_path = os.path.join(project_root, 'data', 'raw')
        else:
            self.base_path = base_path
            
        self.today = datetime.now().strftime("%Y%m%d")
        
        # 创建数据保存目录
        self.data_dir = os.path.join(self.base_path, data_source_name, self.today)
        os.makedirs(self.data_dir, exist_ok=True)
        
        logger.info(f"初始化数据抓取器: {data_source_name}, 保存路径: {self.data_dir}")
    
    @abstractmethod
    def fetch_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        抓取股票数据 - 子类必须实现
        
        Args:
            symbol: 股票代码
            start_date: 开始日期，格式 YYYY-MM-DD
            end_date: 结束日期，格式 YYYY-MM-DD
            
        Returns:
            包含股票数据的DataFrame，列名为: date, open, high, low, close, volume, adj_close
        """
        pass
    
    @abstractmethod
    def get_stock_list(self) -> List[Dict[str, str]]:
        """
        获取股票列表 - 子类必须实现
        
        Returns:
            股票列表，每个元素包含 {'symbol': '股票代码', 'name': '股票名称'}
        """
        pass
    
    def save_data(self, symbol: str, data: pd.DataFrame) -> str:
        """
        保存数据到文件
        
        Args:
            symbol: 股票代码
            data: 股票数据
            
        Returns:
            保存的文件路径
        """
        if data.empty:
            logger.warning(f"数据为空，跳过保存: {symbol}")
            return None
            
        # 确保数据格式正确
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            logger.error(f"数据缺少必要列: {missing_columns}")
            return None
        
        # 保存文件
        file_path = os.path.join(self.data_dir, f"{symbol}.csv")
        
        try:
            # 确保日期列格式正确
            if 'date' in data.columns:
                data['date'] = pd.to_datetime(data['date']).dt.strftime('%Y-%m-%d')
            
            # 保存为CSV文件
            data[required_columns].to_csv(file_path, index=False)
            logger.info(f"数据已保存: {file_path}, 行数: {len(data)}")
            return file_path
            
        except Exception as e:
            logger.error(f"保存数据失败: {symbol}, 错误: {e}")
            return None
    
    def fetch_and_save(self, symbol: str, start_date: str = None, end_date: str = None) -> str:
        """
        抓取并保存数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            保存的文件路径
        """
        logger.info(f"开始抓取数据: {symbol} ({self.data_source_name})")
        
        try:
            # 抓取数据
            data = self.fetch_stock_data(symbol, start_date, end_date)
            
            if data.empty:
                logger.warning(f"未获取到数据: {symbol}")
                return None
            
            # 保存数据
            file_path = self.save_data(symbol, data)
            return file_path
            
        except Exception as e:
            logger.error(f"抓取数据失败: {symbol}, 错误: {e}")
            return None
    
    def batch_fetch(self, symbols: List[str], start_date: str = None, end_date: str = None) -> Dict[str, str]:
        """
        批量抓取数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            字典，键为股票代码，值为保存的文件路径
        """
        logger.info(f"开始批量抓取数据: {len(symbols)}只股票")
        
        results = {}
        for symbol in symbols:
            file_path = self.fetch_and_save(symbol, start_date, end_date)
            results[symbol] = file_path
            
        success_count = sum(1 for path in results.values() if path is not None)
        logger.info(f"批量抓取完成: 成功{success_count}/{len(symbols)}只股票")
        
        return results
    
    def get_saved_file_path(self, symbol: str) -> str:
        """
        获取已保存文件的路径
        
        Args:
            symbol: 股票代码
            
        Returns:
            文件路径
        """
        return os.path.join(self.data_dir, f"{symbol}.csv")
    
    def load_saved_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        加载已保存的数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            股票数据DataFrame，如果文件不存在则返回None
        """
        file_path = self.get_saved_file_path(symbol)
        
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return None
            
        try:
            data = pd.read_csv(file_path)
            logger.info(f"加载数据成功: {symbol}, 行数: {len(data)}")
            return data
        except Exception as e:
            logger.error(f"加载数据失败: {symbol}, 错误: {e}")
            return None 