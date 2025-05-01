from typing import Dict, Any
import pandas as pd
import numpy as np
from .base import StrategyBase
import logging

# 获取logger
logger = logging.getLogger(__name__)

class MovingAverageStrategy(StrategyBase):
    """
    移动平均线交叉策略
    
    当短期移动平均线上穿长期移动平均线时买入
    当短期移动平均线下穿长期移动平均线时卖出
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        """
        初始化移动平均线策略
        
        Args:
            parameters: 策略参数字典，包含 short_window 和 long_window
        """
        default_params = {
            'short_window': 5,   # 短期移动平均线窗口
            'long_window': 20    # 长期移动平均线窗口
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("移动平均线交叉策略", default_params)
        
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
        short_window = self.parameters.get('short_window', 5)
        long_window = self.parameters.get('long_window', 20)
        
        # 计算短期和长期移动平均线
        signals['short_ma'] = signals['close'].rolling(window=short_window, min_periods=1).mean()
        signals['long_ma'] = signals['close'].rolling(window=long_window, min_periods=1).mean()
        
        # 初始化信号列
        signals['signal'] = 0
        
        # 生成信号：1表示买入，-1表示卖出
        # 计算短期均线和长期均线的差值
        signals['ma_diff'] = signals['short_ma'] - signals['long_ma']
        
        # 计算信号：短期均线上穿长期均线为买入信号，下穿为卖出信号
        # 使用移位操作检测穿越
        signals['prev_ma_diff'] = signals['ma_diff'].shift(1)
        
        # 初始几个数据点可能没有前一天的数据，设置为0避免误判
        signals['prev_ma_diff'].fillna(0, inplace=True)
        
        # 上穿信号：今天短期均线在长期均线上方，但昨天在下方或重合
        crossing_up = (signals['ma_diff'] > 0) & (signals['prev_ma_diff'] <= 0)
        signals.loc[crossing_up, 'signal'] = 1
        
        # 记录买入信号触发原因
        for idx in signals.index[crossing_up]:
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            reason = f"买入信号触发 [{date_str}]: 短期均线({short_window}日)上穿长期均线({long_window}日), " \
                    f"短期均线: {signals.loc[idx, 'short_ma']:.2f}, " \
                    f"长期均线: {signals.loc[idx, 'long_ma']:.2f}, " \
                    f"价差: {signals.loc[idx, 'ma_diff']:.2f}, " \
                    f"昨日价差: {signals.loc[idx, 'prev_ma_diff']:.2f}, " \
                    f"收盘价: {signals.loc[idx, 'close']:.2f}"
            logger.info(reason)
            # 添加触发原因到信号数据中
            signals.loc[idx, 'trigger_reason'] = f"短期均线({short_window}日)上穿长期均线({long_window}日)"
        
        # 下穿信号：今天短期均线在长期均线下方，但昨天在上方或重合
        crossing_down = (signals['ma_diff'] < 0) & (signals['prev_ma_diff'] >= 0)
        signals.loc[crossing_down, 'signal'] = -1
        
        # 记录卖出信号触发原因
        for idx in signals.index[crossing_down]:
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            reason = f"卖出信号触发 [{date_str}]: 短期均线({short_window}日)下穿长期均线({long_window}日), " \
                    f"短期均线: {signals.loc[idx, 'short_ma']:.2f}, " \
                    f"长期均线: {signals.loc[idx, 'long_ma']:.2f}, " \
                    f"价差: {signals.loc[idx, 'ma_diff']:.2f}, " \
                    f"昨日价差: {signals.loc[idx, 'prev_ma_diff']:.2f}, " \
                    f"收盘价: {signals.loc[idx, 'close']:.2f}"
            logger.info(reason)
            # 添加触发原因到信号数据中
            signals.loc[idx, 'trigger_reason'] = f"短期均线({short_window}日)下穿长期均线({long_window}日)"
        
        # 持仓信号：根据移动平均线的相对位置判断
        signals.loc[signals['short_ma'] > signals['long_ma'], 'position'] = 1
        signals.loc[signals['short_ma'] <= signals['long_ma'], 'position'] = -1
        
        # 添加其他必要的信息
        signals['symbol'] = signals['symbol'] if 'symbol' in signals.columns else self.data['symbol'].iloc[0] if 'symbol' in self.data.columns else 'default'
        
        return signals 