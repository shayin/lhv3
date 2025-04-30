import os
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import talib

from ..config import PROCESSED_DATA_DIR

logger = logging.getLogger(__name__)

class DataProcessor:
    """数据处理器，用于清洗、处理和特征工程"""
    
    def __init__(self):
        """初始化数据处理器"""
        self.feature_functions = {
            "sma": self._add_sma,
            "ema": self._add_ema,
            "macd": self._add_macd,
            "rsi": self._add_rsi,
            "bollinger_bands": self._add_bollinger_bands
        }
    
    def process_data(self, data, features=None):
        """处理数据，包括清洗和添加特征
        
        Args:
            data (pandas.DataFrame): 原始数据
            features (list, optional): 要添加的特征列表
            
        Returns:
            pandas.DataFrame: 处理后的数据
        """
        if data is None or data.empty:
            logger.warning("没有数据可处理")
            return pd.DataFrame()
            
        # 确保日期列是datetime类型
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            
        # 创建一个副本以避免修改原始数据
        processed_data = data.copy()
        
        # 确保数据包含必要的列
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in processed_data.columns]
        
        if missing_columns:
            logger.error(f"数据缺少必要的列: {', '.join(missing_columns)}")
            return pd.DataFrame()
        
        # 排序数据
        processed_data = processed_data.sort_values('date').reset_index(drop=True)
        
        # 添加特征
        if features:
            for feature in features:
                if feature in self.feature_functions:
                    processed_data = self.feature_functions[feature](processed_data)
                else:
                    logger.warning(f"不支持的特征: {feature}")
        
        return processed_data
    
    def _clean_data(self, data):
        """清洗数据，处理缺失值、异常值等"""
        # 复制数据，避免修改原始数据
        df = data.copy()
        
        # 确保日期列是日期类型
        if 'date' in df.columns:
            if df['date'].dtype != 'datetime64[ns]':
                df['date'] = pd.to_datetime(df['date'])
            
        # 确保价格和交易量为数值类型
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 检查并处理缺失值
        if df.isnull().any().any():
            # 对于OHLC价格，使用前向填充方法
            price_cols = ['open', 'high', 'low', 'close']
            df[price_cols] = df[price_cols].fillna(method='ffill')
            
            # 对于交易量，用0填充缺失值
            if 'volume' in df.columns:
                df['volume'] = df['volume'].fillna(0)
        
        # 排序并重置索引
        if 'date' in df.columns:
            df = df.sort_values('date').reset_index(drop=True)
        
        return df
    
    def _add_sma(self, data, periods=[5, 10, 20, 50, 200]):
        """添加简单移动平均线"""
        for period in periods:
            data[f'sma_{period}'] = data['close'].rolling(window=period).mean()
        return data
    
    def _add_ema(self, data, periods=[5, 10, 20, 50, 200]):
        """添加指数移动平均线"""
        for period in periods:
            data[f'ema_{period}'] = data['close'].ewm(span=period, adjust=False).mean()
        return data
    
    def _add_macd(self, data, fast_period=12, slow_period=26, signal_period=9):
        """添加MACD指标"""
        # 计算快线和慢线
        data['ema_fast'] = data['close'].ewm(span=fast_period, adjust=False).mean()
        data['ema_slow'] = data['close'].ewm(span=slow_period, adjust=False).mean()
        
        # MACD线 = 快线 - 慢线
        data['macd'] = data['ema_fast'] - data['ema_slow']
        
        # 信号线 = MACD的EMA
        data['macd_signal'] = data['macd'].ewm(span=signal_period, adjust=False).mean()
        
        # MACD柱状图 = MACD线 - 信号线
        data['macd_hist'] = data['macd'] - data['macd_signal']
        
        return data
    
    def _add_rsi(self, data, period=14):
        """添加RSI指标"""
        delta = data['close'].diff()
        
        # 上涨和下跌
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        
        # 计算均值
        avg_up = up.rolling(window=period).mean()
        avg_down = down.rolling(window=period).mean()
        
        # 计算相对强度
        rs = avg_up / avg_down
        
        # 计算RSI
        data['rsi'] = 100 - (100 / (1 + rs))
        
        return data
    
    def _add_bollinger_bands(self, data, period=20, num_std=2):
        """添加布林带指标"""
        # 计算中轨线(移动平均线)
        data['bb_middle'] = data['close'].rolling(window=period).mean()
        
        # 计算标准差
        data['bb_std'] = data['close'].rolling(window=period).std()
        
        # 计算上轨和下轨
        data['bb_upper'] = data['bb_middle'] + (data['bb_std'] * num_std)
        data['bb_lower'] = data['bb_middle'] - (data['bb_std'] * num_std)
        
        return data
    
    def save_processed_data(self, data, symbol, features=None):
        """保存处理后的数据到文件"""
        if data is None or data.empty:
            return None
            
        symbol_safe = symbol.replace(".", "_")
        feature_str = "_".join(features) if features else "raw"
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{symbol_safe}_{feature_str}_{date_str}.csv"
        filepath = os.path.join(PROCESSED_DATA_DIR, filename)
        
        data.to_csv(filepath, index=False)
        logger.info(f"处理后的数据已保存至: {filepath}")
        
        return filepath 