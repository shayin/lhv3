from typing import Dict, Any
import pandas as pd
import numpy as np
from .base import StrategyBase

class RSIStrategy(StrategyBase):
    """
    相对强弱指标(RSI)策略
    
    当RSI低于超卖阈值时买入
    当RSI高于超买阈值时卖出
    """
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化RSI策略
        
        Args:
            params: 策略参数字典，包含 period, overbought, oversold
        """
        default_params = {
            'period': 14,       # RSI计算周期
            'overbought': 70,   # 超买阈值
            'oversold': 30      # 超卖阈值
        }
        
        if params:
            default_params.update(params)
            
        super().__init__(default_params)
        self.name = "rsi"
        
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        计算相对强弱指标(RSI)
        
        Args:
            prices: 价格序列
            period: 计算周期
            
        Returns:
            RSI值序列
        """
        # 计算价格变化
        delta = prices.diff()
        
        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 计算平均上涨和下跌
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 计算相对强度
        rs = avg_gain / avg_loss.where(avg_loss != 0, 0.001)  # 避免除以零
        
        # 计算RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        根据价格数据生成交易信号
        
        Args:
            data: 包含价格数据的DataFrame，需要包含'close'列
            
        Returns:
            添加了信号列的DataFrame
        """
        # 复制数据以避免修改原始数据
        signals = data.copy()
        
        # 获取参数
        period = self.params['period']
        overbought = self.params['overbought']
        oversold = self.params['oversold']
        
        # 计算RSI
        signals['rsi'] = self._calculate_rsi(signals['close'], period)
        
        # 初始化信号列
        signals['signal'] = 0
        
        # 生成信号
        # RSI低于超卖阈值时买入
        signals.loc[signals['rsi'] < oversold, 'signal'] = 1
        # RSI高于超买阈值时卖出
        signals.loc[signals['rsi'] > overbought, 'signal'] = -1
        
        return signals 