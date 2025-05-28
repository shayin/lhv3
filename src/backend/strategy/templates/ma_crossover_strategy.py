from src.backend.strategy.templates.strategy_template import StrategyTemplate
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MACrossoverStrategy(StrategyTemplate):
    """
    移动平均线交叉策略
    当MA5上穿MA20时买入，当MA5下穿MA20时卖出
    """
    
    def __init__(self, parameters=None):
        """初始化策略"""
        default_params = {
            "short_window": 5,   # 短期移动平均窗口
            "long_window": 20,   # 长期移动平均窗口
        }
        
        # 合并用户参数与默认参数
        if parameters:
            default_params.update(parameters)
            
        super().__init__(name="MA交叉策略", parameters=default_params)
        
    def generate_signals(self) -> pd.DataFrame:
        """
        生成交易信号
        
        Returns:
            包含信号的DataFrame，包括:
            - signal: 交易信号 (1: 买入, -1: 卖出, 0: 不操作)
            - trigger_reason: 信号触发原因
        """
        if self.data is None or self.data.empty:
            logger.warning("未设置数据或数据为空，无法生成信号")
            return pd.DataFrame()
        
        # 获取参数
        short_window = self.parameters["short_window"]
        long_window = self.parameters["long_window"]
        
        logger.info(f"生成MA交叉信号: 短期窗口={short_window}, 长期窗口={long_window}")
        
        # 计算指标
        df = self.data.copy()
        
        # 计算移动平均线
        df[f'ma_{short_window}'] = df['close'].rolling(window=short_window).mean()
        df[f'ma_{long_window}'] = df['close'].rolling(window=long_window).mean()
        
        # 计算当前日期和前一日期的移动平均线差值
        df['ma_diff'] = df[f'ma_{short_window}'] - df[f'ma_{long_window}']
        df['prev_ma_diff'] = df['ma_diff'].shift(1)
        
        # 初始化信号列
        df['signal'] = 0
        df['trigger_reason'] = ''
        
        # 生成买入信号：短期均线从下方上穿长期均线
        buy_signal = (df['ma_diff'] > 0) & (df['prev_ma_diff'] <= 0)
        df.loc[buy_signal, 'signal'] = 1
        df.loc[buy_signal, 'trigger_reason'] = f"MA{short_window}从下方上穿MA{long_window}"
        
        # 生成卖出信号：短期均线从上方下穿长期均线
        sell_signal = (df['ma_diff'] < 0) & (df['prev_ma_diff'] >= 0)
        df.loc[sell_signal, 'signal'] = -1
        df.loc[sell_signal, 'trigger_reason'] = f"MA{short_window}从上方下穿MA{long_window}"
        
        # 统计信号数量
        buy_count = (df['signal'] == 1).sum()
        sell_count = (df['signal'] == -1).sum()
        logger.info(f"信号统计: 买入信号={buy_count}个, 卖出信号={sell_count}个")
        
        return df 