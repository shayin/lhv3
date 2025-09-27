"""
极大极小值策略修正版
修正了使用未来数据的问题，使用滚动窗口来生成信号
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
from src.backend.strategy.templates.strategy_template import StrategyTemplate

logger = logging.getLogger(__name__)

class ExtremumStrategyFixed(StrategyTemplate):
    """
    极大极小值策略修正版
    
    策略逻辑：
    1. 使用滚动窗口寻找局部极值
    2. 在局部最小值时买入
    3. 在局部最大值时卖出
    4. 不使用未来数据，只使用当前及之前的数据
    """
    
    def __init__(self, name: str = "极大极小值策略修正版", data: pd.DataFrame = None, parameters: Dict[str, Any] = None):
        """
        初始化极大极小值策略修正版
        
        Args:
            name: 策略名称
            data: 数据
            parameters: 策略参数字典
        """
        default_params = {
            'window_size': 20,      # 滚动窗口大小
            'min_periods': 10,      # 最小计算周期
            'min_change_pct': 0.05,  # 最小变化百分比（5%）
            'max_hold_days': 30,     # 最大持仓天数
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__(name, data, default_params)
        
    def generate_signals(self):
        """
        生成交易信号 - 修正版，不使用未来数据
        
        Returns:
            添加了信号列的DataFrame
        """
        if self.data is None:
            raise ValueError("未设置数据，无法生成信号")
            
        # 复制数据以避免修改原始数据
        signals = self.data.copy()
        
        # 获取参数
        window_size = self.parameters.get('window_size', 20)
        min_periods = self.parameters.get('min_periods', 10)
        min_change_pct = self.parameters.get('min_change_pct', 0.05)
        max_hold_days = self.parameters.get('max_hold_days', 30)
        
        logger.info(f"生成极大极小值信号修正版 - 窗口: {window_size}, 最小变化: {min_change_pct*100}%")
        
        # 初始化信号列
        signals['signal'] = 0
        signals['trigger_reason'] = ''
        
        # 计算滚动窗口的极值（只使用当前及之前的数据）
        signals['rolling_max'] = signals['close'].rolling(
            window=window_size, 
            min_periods=min_periods
        ).max()
        
        signals['rolling_min'] = signals['close'].rolling(
            window=window_size, 
            min_periods=min_periods
        ).min()
        
        # 计算价格变化百分比
        signals['change_from_min'] = (signals['close'] - signals['rolling_min']) / signals['rolling_min']
        signals['change_from_max'] = (signals['close'] - signals['rolling_max']) / signals['rolling_max']
        
        # 初始化持仓状态
        position = 0  # 0: 空仓, 1: 持仓
        buy_price = 0
        buy_date = None
        hold_days = 0
        
        # 逐日生成信号（不使用未来数据）
        for i in range(len(signals)):
            current_date = signals.index[i]
            current_price = signals.loc[current_date, 'close']
            current_rolling_max = signals.loc[current_date, 'rolling_max']
            current_rolling_min = signals.loc[current_date, 'rolling_min']
            current_change_from_min = signals.loc[current_date, 'change_from_min']
            current_change_from_max = signals.loc[current_date, 'change_from_max']
            
            # 更新持仓天数
            if position == 1:
                hold_days += 1
            
            # 买入信号：价格接近滚动窗口最小值
            if (position == 0 and 
                not pd.isna(current_rolling_min) and 
                current_price <= current_rolling_min * (1 + min_change_pct)):
                
                signals.loc[current_date, 'signal'] = 1
                signals.loc[current_date, 'trigger_reason'] = f"价格接近{window_size}日最低点"
                position = 1
                buy_price = current_price
                buy_date = current_date
                hold_days = 0
                
                logger.info(f"买入信号 [{current_date}]: 价格 {current_price:.2f} 接近{window_size}日最低点 {current_rolling_min:.2f}")
            
            # 卖出信号：价格接近滚动窗口最大值 或 达到最大持仓天数
            elif (position == 1 and 
                  ((not pd.isna(current_rolling_max) and 
                    current_price >= current_rolling_max * (1 - min_change_pct)) or
                   hold_days >= max_hold_days)):
                
                signals.loc[current_date, 'signal'] = -1
                if hold_days >= max_hold_days:
                    signals.loc[current_date, 'trigger_reason'] = f"达到最大持仓天数({max_hold_days}天)"
                else:
                    signals.loc[current_date, 'trigger_reason'] = f"价格接近{window_size}日最高点"
                
                position = 0
                profit_pct = (current_price - buy_price) / buy_price * 100
                logger.info(f"卖出信号 [{current_date}]: 价格 {current_price:.2f} 接近{window_size}日最高点 {current_rolling_max:.2f}, 收益: {profit_pct:.2f}%")
        
        # 添加持仓信号
        signals['position'] = 0
        current_position = 0
        for i in range(len(signals)):
            if signals.iloc[i]['signal'] == 1:
                current_position = 1
            elif signals.iloc[i]['signal'] == -1:
                current_position = 0
            signals.iloc[i, signals.columns.get_loc('position')] = current_position
        
        # 统计信号数量
        buy_signals = (signals['signal'] == 1).sum()
        sell_signals = (signals['signal'] == -1).sum()
        
        logger.info(f"信号生成完成 - 买入信号: {buy_signals}, 卖出信号: {sell_signals}")
        
        return signals
