from typing import Dict, Any
import pandas as pd
import numpy as np
from .base import StrategyBase

class RSIStrategy(StrategyBase):
    """
    相对强弱指数(RSI)策略
    
    当RSI低于超卖阈值时买入
    当RSI高于超买阈值时卖出
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        """
        初始化RSI策略
        
        Args:
            parameters: 策略参数字典，包含 period, overbought, oversold
        """
        default_params = {
            'period': 14,      # RSI计算周期
            'overbought': 70,  # 超买阈值
            'oversold': 30     # 超卖阈值
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("相对强弱指数(RSI)策略", default_params)
        
    def generate_signals(self):
        """
        根据价格数据生成交易信号
        
        Returns:
            添加了信号列的DataFrame
        """
        if self.data is None:
            raise ValueError("未设置数据，无法生成信号")
            
        # 复制数据以避免修改原始数据
        signals = self.data.copy()
        
        # 获取参数
        period = self.parameters.get('period', 14)
        overbought = self.parameters.get('overbought', 70)
        oversold = self.parameters.get('oversold', 30)
        
        # 计算价格变动
        signals['price_change'] = signals['close'].diff()
        
        # 分离上涨和下跌
        signals['gain'] = signals['price_change'].clip(lower=0)
        signals['loss'] = -signals['price_change'].clip(upper=0)
        
        # 计算平均上涨和下跌
        signals['avg_gain'] = signals['gain'].rolling(window=period).mean()
        signals['avg_loss'] = signals['loss'].rolling(window=period).mean()
        
        # 计算相对强度(RS)
        signals['rs'] = signals['avg_gain'] / signals['avg_loss'].replace(0, 1e-9)  # 避免除以零
        
        # 计算RSI
        signals['rsi'] = 100 - (100 / (1 + signals['rs']))
        
        # 初始化信号列
        signals['signal'] = 0
        
        # 生成信号：1表示买入，-1表示卖出
        # RSI低于超卖阈值时买入
        signals.loc[signals['rsi'] < oversold, 'signal'] = 1
        
        # RSI高于超买阈值时卖出
        signals.loc[signals['rsi'] > overbought, 'signal'] = -1
        
        # 持仓信号：根据RSI相对于阈值的位置判断
        signals['position'] = 0
        signals.loc[signals['rsi'] < oversold, 'position'] = 1
        signals.loc[signals['rsi'] > overbought, 'position'] = -1
        
        # 添加其他必要的信息
        signals['symbol'] = signals['symbol'] if 'symbol' in signals.columns else self.data['symbol'].iloc[0] if 'symbol' in self.data.columns else 'default'
        
        return signals 