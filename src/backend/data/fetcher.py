import os
import pandas as pd
import yfinance as yf
import akshare as ak
from datetime import datetime, timedelta
import logging

from ..config import RAW_DATA_DIR, PROCESSED_DATA_DIR, API_KEYS

logger = logging.getLogger(__name__)

class DataFetcher:
    """数据获取器，用于从不同数据源获取市场数据"""
    
    def __init__(self):
        self.data_sources = {
            "yahoo": self._fetch_from_yahoo,
            "akshare": self._fetch_from_akshare,
            "local": self._fetch_from_local,
        }
    
    def fetch_data(self, symbol, start_date, end_date=None, data_source="yahoo"):
        """获取指定股票的历史数据
        
        Args:
            symbol (str): 股票代码
            start_date (str): 开始日期，格式：YYYY-MM-DD
            end_date (str, optional): 结束日期，格式：YYYY-MM-DD，默认为今天
            data_source (str, optional): 数据源，默认为yahoo
            
        Returns:
            pandas.DataFrame: 包含历史数据的DataFrame
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        if data_source not in self.data_sources:
            raise ValueError(f"不支持的数据源: {data_source}")
            
        try:
            return self.data_sources[data_source](symbol, start_date, end_date)
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            raise
    
    def _fetch_from_yahoo(self, symbol, start_date, end_date):
        """从Yahoo Finance获取数据"""
        logger.info(f"尝试获取股票数据: {symbol}, 期间: {start_date} 至 {end_date}")
        
        # 1. 首先尝试直接从本地文件加载
        try:
            # 检查所有可能的位置
            possible_files = []
            
            # 检查当前目录
            current_file = f"{symbol}.csv"
            if os.path.exists(current_file):
                possible_files.append(current_file)
                
            # 检查data/raw目录
            raw_data_file = os.path.join(RAW_DATA_DIR, f"{symbol}.csv")
            if os.path.exists(raw_data_file):
                possible_files.append(raw_data_file)
                
            # 检查data/raw目录下的其他匹配文件
            if os.path.exists(RAW_DATA_DIR):
                for f in os.listdir(RAW_DATA_DIR):
                    if f.startswith(f"{symbol}_") and f.endswith(".csv"):
                        possible_files.append(os.path.join(RAW_DATA_DIR, f))
            
            # 如果找到了文件，加载最新的一个
            if possible_files:
                possible_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                selected_file = possible_files[0]
                logger.info(f"从本地文件加载数据: {selected_file}")
                
                # 读取CSV文件
                data = pd.read_csv(selected_file)
                
                # 确保日期列是datetime格式
                if 'date' in data.columns:
                    data['date'] = pd.to_datetime(data['date'])
                    
                    # 过滤日期范围
                    start_date_dt = pd.to_datetime(start_date)
                    end_date_dt = pd.to_datetime(end_date)
                    filtered_data = data[(data['date'] >= start_date_dt) & (data['date'] <= end_date_dt)]
                    
                    if not filtered_data.empty:
                        logger.info(f"成功从本地文件加载数据: {selected_file}, 共{len(filtered_data)}行")
                        return filtered_data
                    else:
                        logger.warning(f"从文件加载的数据在指定日期范围内为空: {selected_file}")
                else:
                    logger.warning(f"文件缺少日期列: {selected_file}")
        except Exception as local_err:
            logger.error(f"从本地文件加载数据失败: {str(local_err)}")
        
        # 2. 如果本地文件不存在或加载失败，尝试从Yahoo Finance获取
        try:
            # 确保美股股票代码格式正确
            if "." not in symbol and not symbol.endswith(".HK"):
                symbol_yahoo = symbol
            else:
                symbol_yahoo = symbol
                
            logger.info(f"从Yahoo Finance获取数据: {symbol_yahoo}")
            stock = yf.Ticker(symbol_yahoo)
            data = stock.history(start=start_date, end=end_date)
            
            # 确保数据格式一致
            if not data.empty:
                data = data.reset_index()
                data.columns = [col.lower() for col in data.columns]
                data = data.rename(columns={"index": "date", "stock splits": "splits"})
                
                # 保存原始数据
                self._save_raw_data(data, symbol, "yahoo")
                logger.info(f"成功从Yahoo Finance获取数据: {symbol}, 共{len(data)}行")
                return data
            else:
                logger.warning(f"从Yahoo Finance获取的数据为空: {symbol}")
        except Exception as yahoo_err:
            logger.error(f"从Yahoo Finance获取数据失败: {str(yahoo_err)}")
            
        # 如果所有方法都失败，返回空DataFrame
        logger.error(f"无法获取股票数据: {symbol}")
        return pd.DataFrame()
    
    def _fetch_from_akshare(self, symbol, start_date, end_date):
        """从AKShare获取A股数据"""
        # 确保A股股票代码格式正确
        if symbol.endswith(".SH") or symbol.endswith(".SZ"):
            symbol_ak = symbol.split(".")[0]
            market = symbol.split(".")[1].lower()
        else:
            # 默认假设为上证
            symbol_ak = symbol
            market = "sh"
        
        try:
            # 获取日线数据
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            start_year = start_date_obj.year
            
            # AKShare获取股票历史数据
            if market == "sh":
                data = ak.stock_zh_a_hist(symbol=symbol_ak, period="daily", 
                                          start_date=start_date, end_date=end_date, 
                                          adjust="qfq")
            else:
                data = ak.stock_zh_a_hist(symbol=symbol_ak, period="daily", 
                                          start_date=start_date, end_date=end_date, 
                                          adjust="qfq")
            
            # 确保数据格式一致
            if not data.empty:
                data.columns = [col.lower() for col in data.columns]
                data = data.rename(columns={"日期": "date", "开盘": "open", "最高": "high", 
                                          "最低": "low", "收盘": "close", "成交量": "volume"})
                
                # 保存原始数据
                self._save_raw_data(data, symbol, "akshare")
                
            return data
            
        except Exception as e:
            logger.error(f"从AKShare获取数据失败: {e}")
            raise
    
    def _fetch_from_local(self, symbol, start_date, end_date):
        """从本地文件获取数据"""
        logger.info(f"尝试从本地文件获取数据: {symbol}, 期间: {start_date} 至 {end_date}")
        
        try:
            # 检查所有可能的位置
            possible_files = []
            
            # 检查当前目录
            current_file = f"{symbol}.csv"
            if os.path.exists(current_file):
                possible_files.append(current_file)
                
            # 检查data/raw目录
            raw_data_file = os.path.join(RAW_DATA_DIR, f"{symbol}.csv")
            if os.path.exists(raw_data_file):
                possible_files.append(raw_data_file)
                
            # 检查data/raw目录下的其他匹配文件
            if os.path.exists(RAW_DATA_DIR):
                for f in os.listdir(RAW_DATA_DIR):
                    if f.startswith(f"{symbol}_") and f.endswith(".csv"):
                        possible_files.append(os.path.join(RAW_DATA_DIR, f))
                        
            # 检查data/processed目录
            processed_data_file = os.path.join(PROCESSED_DATA_DIR, f"{symbol}.csv")
            if os.path.exists(processed_data_file):
                possible_files.append(processed_data_file)
                
            # 检查data/processed目录下的其他匹配文件
            if os.path.exists(PROCESSED_DATA_DIR):
                for f in os.listdir(PROCESSED_DATA_DIR):
                    if f.startswith(f"{symbol}_") and f.endswith(".csv"):
                        possible_files.append(os.path.join(PROCESSED_DATA_DIR, f))
            
            # 如果找到了文件，加载最新的一个
            if possible_files:
                possible_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                selected_file = possible_files[0]
                logger.info(f"从本地文件加载数据: {selected_file}")
                
                # 读取CSV文件
                data = pd.read_csv(selected_file)
                
                # 确保日期列是datetime格式
                if 'date' in data.columns:
                    data['date'] = pd.to_datetime(data['date'])
                    
                    # 过滤日期范围
                    start_date_dt = pd.to_datetime(start_date)
                    end_date_dt = pd.to_datetime(end_date)
                    filtered_data = data[(data['date'] >= start_date_dt) & (data['date'] <= end_date_dt)]
                    
                    if not filtered_data.empty:
                        logger.info(f"成功从本地文件加载数据: {selected_file}, 共{len(filtered_data)}行")
                        return filtered_data
                    else:
                        # 如果过滤后的数据为空，就返回全部数据，让调用方进行日期范围调整
                        logger.warning(f"从文件加载的数据在指定日期范围内为空: {selected_file}，返回全部可用数据")
                        return data
                else:
                    logger.warning(f"文件缺少日期列: {selected_file}")
                    # 如果没有日期列，返回全部数据
                    return data
            
            logger.error(f"在本地找不到{symbol}的数据文件")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"从本地文件加载数据失败: {str(e)}")
            return pd.DataFrame()
    
    def _save_raw_data(self, data, symbol, source):
        """保存原始数据到文件"""
        if data is None or data.empty:
            return
            
        symbol_safe = symbol.replace(".", "_")
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{symbol_safe}_{source}_{date_str}.csv"
        filepath = os.path.join(RAW_DATA_DIR, filename)
        
        data.to_csv(filepath, index=False)
        logger.info(f"原始数据已保存至: {filepath}")
        
        return filepath 