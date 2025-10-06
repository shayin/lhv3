import pandas as pd
import numpy as np
import hashlib
from typing import Dict, Any, Optional, List
import logging

from ...utils.cache import indicator_cache

logger = logging.getLogger(__name__)

class StrategyTemplate:
    """
    策略模板类，所有自定义策略必须继承此类。
    实现所有必要的方法以确保策略在平台上正常运行。
    """
    
    def __init__(self, name: str = "策略模板", data: pd.DataFrame = None, parameters: Dict[str, Any] = None):
        """
        初始化策略
        
        Args:
            name: 策略名称
            parameters: 策略参数字典
        """
        self.name = name
        self.parameters = parameters or {}
        self.data = data
        
    def set_data(self, data: pd.DataFrame) -> None:
        """
        设置策略使用的数据
        
        Args:
            data: 市场数据，必须包含 date, open, high, low, close, volume 等基本列
        """
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            raise ValueError(f"数据缺少必要的列: {missing_columns}")
            
        self.data = data
        logger.info(f"数据已设置: {len(data)}行, 从{data['date'].min()}到{data['date'].max()}")
    
    def initialize(self, initial_capital: float = 100000.0) -> None:
        """
        初始化策略，设置初始资金等参数
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        logger.info(f"初始化策略资金: {initial_capital}")
    
    def generate_signals(self) -> pd.DataFrame:
        """
        生成交易信号 - 必须由子类实现
        
        Returns:
            包含以下列的DataFrame:
            - signal: 交易信号，1表示买入，-1表示卖出，0表示不操作
            - trigger_reason: 触发原因，描述信号产生的原因
        """
        if self.data is None or self.data.empty:
            return pd.DataFrame()
            
        # 子类必须覆盖此方法并生成信号
        raise NotImplementedError("子类必须实现generate_signals方法")
    
    def _get_data_hash(self) -> str:
        """生成数据哈希值，用于缓存验证"""
        if self.data is None:
            return ""
        
        # 使用数据的形状、列名和前后几行数据生成哈希
        data_info = {
            'shape': self.data.shape,
            'columns': list(self.data.columns),
            'head': self.data.head(3).to_dict() if len(self.data) > 0 else {},
            'tail': self.data.tail(3).to_dict() if len(self.data) > 2 else {}
        }
        
        data_str = str(data_info)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _calculate_ma_with_cache(self, symbol: str, period: int, data_hash: str) -> pd.Series:
        """带缓存的移动平均线计算"""
        cache_key = f"ma_{period}"
        params = {'period': period}
        
        # 尝试从缓存获取
        cached_result = indicator_cache.get_indicator(symbol, cache_key, params, data_hash)
        if cached_result is not None:
            logger.debug(f"使用缓存的MA{period}指标")
            return cached_result
        
        # 计算指标
        ma_result = self.data['close'].rolling(window=period).mean()
        
        # 缓存结果
        indicator_cache.set_indicator(symbol, cache_key, params, data_hash, ma_result)
        logger.debug(f"计算并缓存MA{period}指标")
        
        return ma_result
    
    def _calculate_rsi_with_cache(self, symbol: str, period: int, data_hash: str) -> pd.Series:
        """带缓存的RSI计算"""
        cache_key = f"rsi_{period}"
        params = {'period': period}
        
        # 尝试从缓存获取
        cached_result = indicator_cache.get_indicator(symbol, cache_key, params, data_hash)
        if cached_result is not None:
            logger.debug(f"使用缓存的RSI{period}指标")
            return cached_result
        
        # 计算RSI
        def calculate_rsi(prices, period=14):
            delta = prices.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
            rs = gain / loss.replace(0, 1e-9)  # 避免除以零
            return 100 - (100 / (1 + rs))
        
        rsi_result = calculate_rsi(self.data['close'], period)
        
        # 缓存结果
        indicator_cache.set_indicator(symbol, cache_key, params, data_hash, rsi_result)
        logger.debug(f"计算并缓存RSI{period}指标")
        
        return rsi_result
    
    def _calculate_macd_with_cache(self, symbol: str, fast: int, slow: int, signal: int, data_hash: str) -> tuple:
        """带缓存的MACD计算"""
        cache_key = f"macd_{fast}_{slow}_{signal}"
        params = {'fast': fast, 'slow': slow, 'signal': signal}
        
        # 尝试从缓存获取
        cached_result = indicator_cache.get_indicator(symbol, cache_key, params, data_hash)
        if cached_result is not None:
            logger.debug(f"使用缓存的MACD指标")
            return cached_result
        
        # 计算MACD
        def calculate_macd(prices, fast=12, slow=26, signal=9):
            ema_fast = prices.ewm(span=fast, adjust=False).mean()
            ema_slow = prices.ewm(span=slow, adjust=False).mean()
            macd = ema_fast - ema_slow
            macd_signal = macd.ewm(span=signal, adjust=False).mean()
            macd_hist = macd - macd_signal
            return macd, macd_signal, macd_hist
        
        macd_result = calculate_macd(self.data['close'], fast, slow, signal)
        
        # 缓存结果
        indicator_cache.set_indicator(symbol, cache_key, params, data_hash, macd_result)
        logger.debug(f"计算并缓存MACD指标")
        
        return macd_result
    
    def _calculate_bollinger_bands_with_cache(self, symbol: str, window: int, num_std: int, data_hash: str) -> tuple:
        """带缓存的布林带计算"""
        cache_key = f"bb_{window}_{num_std}"
        params = {'window': window, 'num_std': num_std}
        
        # 尝试从缓存获取
        cached_result = indicator_cache.get_indicator(symbol, cache_key, params, data_hash)
        if cached_result is not None:
            logger.debug(f"使用缓存的布林带指标")
            return cached_result
        
        # 计算布林带
        def calculate_bollinger_bands(prices, window=20, num_std=2):
            middle = prices.rolling(window=window).mean()
            std = prices.rolling(window=window).std()
            upper = middle + (std * num_std)
            lower = middle - (std * num_std)
            return upper, middle, lower
        
        bb_result = calculate_bollinger_bands(self.data['close'], window, num_std)
        
        # 缓存结果
        indicator_cache.set_indicator(symbol, cache_key, params, data_hash, bb_result)
        logger.debug(f"计算并缓存布林带指标")
        
        return bb_result

    def calculate_indicators(self) -> pd.DataFrame:
        """
        计算技术指标（带缓存优化）
        
        Returns:
            添加了技术指标的DataFrame
        """
        if self.data is None:
            raise ValueError("未设置数据，无法计算指标")
            
        df = self.data.copy()
        
        # 生成数据哈希用于缓存
        data_hash = self._get_data_hash()
        symbol = getattr(self, 'symbol', 'unknown')  # 获取股票代码，如果没有则使用'unknown'
        
        # 计算常用技术指标（使用缓存）
        # 1. 移动平均线
        for period in [5, 10, 20, 50, 100, 200]:
            df[f'ma_{period}'] = self._calculate_ma_with_cache(symbol, period, data_hash)
        
        # 2. 相对强弱指数(RSI)
        df['rsi_14'] = self._calculate_rsi_with_cache(symbol, 14, data_hash)
        
        # 3. MACD
        macd_result = self._calculate_macd_with_cache(symbol, 12, 26, 9, data_hash)
        df['macd'], df['macd_signal'], df['macd_hist'] = macd_result
        
        # 4. 布林带
        bb_result = self._calculate_bollinger_bands_with_cache(symbol, 20, 2, data_hash)
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = bb_result
        
        return df
    
    def validate(self) -> List[str]:
        """
        验证策略代码是否符合规范
        
        Returns:
            错误消息列表，如果没有错误则为空列表
        """
        errors = []
        
        # 检查是否实现了必要的方法
        if self.generate_signals.__qualname__ == 'StrategyTemplate.generate_signals':
            errors.append("必须实现generate_signals方法")
        
        return errors 

    def suggest_position_size(self, signal: float, row: Optional[pd.Series] = None) -> Optional[float]:
        """
        可选接口：策略可以覆盖此方法来建议本次交易应该使用的仓位比例（0-1）。

        Args:
            signal: 交易信号值（例如 1 或 -1）
            row: 信号行（pandas.Series），包含信号发生时的指标与上下文

        Returns:
            float | None: 返回建议的仓位比例（0-1），若返回 None 则使用回测引擎的默认计算
        """
        return None