import pandas as pd
import numpy as np
from datetime import datetime
from abc import ABC, abstractmethod
from ..strategy.base import StrategyBase

class MovingAverageCrossover(StrategyBase):
    """移动平均线交叉策略"""
    
    def __init__(self, parameters=None):
        """
        初始化策略
        
        Args:
            parameters (dict, optional): 策略参数
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 参数类型检查
        if parameters is not None and not isinstance(parameters, dict):
            logger.error(f"MovingAverageCrossover.__init__: parameters参数类型错误，期望dict，实际为{type(parameters)}")
            parameters = {}  # 重置为空字典以避免后续错误
        
        default_params = {
            'short_window': 5,      # 短期均线周期
            'long_window': 20,      # 长期均线周期
            'commission_rate': 0.0003  # 手续费率
        }
        
        if parameters:
            default_params.update(parameters)
        
        # 调用父类初始化方法
        super().__init__(default_params, "移动平均线交叉策略")

    def generate_signals(self, data: pd.DataFrame = None):
        """
        生成交易信号
        
        Args:
            data: 可选，包含价格数据的DataFrame，如果为None则使用self.data
            
        Returns:
            pandas.DataFrame: 包含交易信号的DataFrame
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 如果提供了data参数，使用它；否则使用self.data
        if data is None:
            data = self.data
        
        if data is None or data.empty:
            logger.error("没有数据可生成信号")
            return pd.DataFrame()
            
        df = data.copy()
        
        # 参数获取
        short_window = int(self.parameters.get('short_window', 5))
        long_window = int(self.parameters.get('long_window', 20))
        
        logger.info(f"生成移动平均线交叉信号 - 短期: {short_window}日, 长期: {long_window}日")
        
        # 数据检查
        required_cols = ['close']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"数据缺少必要的列: {missing_cols}")
            return pd.DataFrame()
            
        # 确保有足够的数据计算移动平均线
        if len(df) < long_window:
            logger.warning(f"数据点数({len(df)})少于长期均线周期({long_window})，可能导致信号不准确")
        
        # 计算移动平均线
        logger.info("计算短期和长期移动平均线")
        df['short_ma'] = df['close'].rolling(window=short_window, min_periods=1).mean()
        df['long_ma'] = df['close'].rolling(window=long_window, min_periods=1).mean()
        
        # 初始化信号列
        df['signal'] = 0
        
        # 计算短期均线和长期均线的差值
        df['ma_diff'] = df['short_ma'] - df['long_ma']
        
        # 计算信号：短期均线上穿长期均线为买入信号，下穿为卖出信号
        # 使用移位操作检测穿越
        df['prev_ma_diff'] = df['ma_diff'].shift(1)
        
        # 初始几个数据点可能没有前一天的数据，设置为0避免误判
        df['prev_ma_diff'].fillna(0, inplace=True)
        
        # 上穿信号：今天短期均线在长期均线上方，但昨天在下方或重合
        crossover_up = (df['ma_diff'] > 0) & (df['prev_ma_diff'] <= 0)
        df.loc[crossover_up, 'signal'] = 1
        
        # 记录买入信号触发原因
        for idx in df.index[crossover_up]:
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            reason = f"买入信号触发 [{date_str}]: 短期均线({short_window}日)上穿长期均线({long_window}日), " \
                    f"短期均线: {df.loc[idx, 'short_ma']:.2f}, " \
                    f"长期均线: {df.loc[idx, 'long_ma']:.2f}, " \
                    f"价差: {df.loc[idx, 'ma_diff']:.2f}, " \
                    f"昨日价差: {df.loc[idx, 'prev_ma_diff']:.2f}, " \
                    f"收盘价: {df.loc[idx, 'close']:.2f}"
            logger.info(reason)
            # 添加触发原因到信号数据中
            df.loc[idx, 'trigger_reason'] = f"短期均线({short_window}日)上穿长期均线({long_window}日)"
        
        # 下穿信号：今天短期均线在长期均线下方，但昨天在上方或重合
        crossover_down = (df['ma_diff'] < 0) & (df['prev_ma_diff'] >= 0)
        df.loc[crossover_down, 'signal'] = -1
        
        # 记录卖出信号触发原因
        for idx in df.index[crossover_down]:
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            reason = f"卖出信号触发 [{date_str}]: 短期均线({short_window}日)下穿长期均线({long_window}日), " \
                    f"短期均线: {df.loc[idx, 'short_ma']:.2f}, " \
                    f"长期均线: {df.loc[idx, 'long_ma']:.2f}, " \
                    f"价差: {df.loc[idx, 'ma_diff']:.2f}, " \
                    f"昨日价差: {df.loc[idx, 'prev_ma_diff']:.2f}, " \
                    f"收盘价: {df.loc[idx, 'close']:.2f}"
            logger.info(reason)
            # 添加触发原因到信号数据中
            df.loc[idx, 'trigger_reason'] = f"短期均线({short_window}日)下穿长期均线({long_window}日)"
        
        # 持仓信号：根据移动平均线的相对位置判断
        df.loc[df['short_ma'] > df['long_ma'], 'position'] = 1
        df.loc[df['short_ma'] <= df['long_ma'], 'position'] = -1
        
        # 忽略无法计算移动平均线的部分
        df['signal'].iloc[:long_window] = 0
        
        # 添加其他必要的信息
        df['symbol'] = df['symbol'] if 'symbol' in df.columns else self.data['symbol'].iloc[0] if 'symbol' in self.data.columns else 'default'
        
        # 统计买入和卖出信号数量
        buy_signals = (df['signal'] == 1).sum()
        sell_signals = (df['signal'] == -1).sum()
        logger.info(f"生成信号完成 - 买入信号: {buy_signals}个, 卖出信号: {sell_signals}个")
        
        return df

class BollingerBandsStrategy(StrategyBase):
    """布林带策略"""
    
    def __init__(self, parameters=None):
        """
        初始化策略
        
        Args:
            parameters (dict, optional): 策略参数
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 参数类型检查
        if parameters is not None and not isinstance(parameters, dict):
            logger.error(f"BollingerBandsStrategy.__init__: parameters参数类型错误，期望dict，实际为{type(parameters)}")
            parameters = {}  # 重置为空字典以避免后续错误
            
        default_params = {
            'window': 20,          # 移动平均窗口
            'num_std': 2,          # 标准差倍数
            'commission_rate': 0.0003  # 手续费率
        }
        
        if parameters:
            default_params.update(parameters)
            
        # 调用父类初始化方法
        super().__init__(default_params, "布林带策略")
    
    def generate_signals(self, data: pd.DataFrame = None):
        """
        生成交易信号
        
        Args:
            data: 可选，包含价格数据的DataFrame，如果为None则使用self.data
            
        Returns:
            pandas.DataFrame: 包含交易信号的DataFrame
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 如果提供了data参数，使用它；否则使用self.data
        if data is None:
            data = self.data
            
        if data is None or data.empty:
            logger.error("没有数据可生成信号")
            return pd.DataFrame()
            
        df = data.copy()
        
        # 计算布林带
        window = int(self.parameters.get('window', 20))
        num_std = float(self.parameters.get('num_std', 2.0))
        
        logger.info(f"生成布林带信号 - 窗口: {window}, 标准差倍数: {num_std}")
        
        # 计算布林带指标
        df['middle'] = df['close'].rolling(window=window, min_periods=1).mean()
        df['std'] = df['close'].rolling(window=window, min_periods=1).std()
        df['upper'] = df['middle'] + (df['std'] * num_std)
        df['lower'] = df['middle'] - (df['std'] * num_std)
        
        # 初始化信号列
        df['signal'] = 0
        
        # 计算前一天的价格与布林带位置
        df['prev_close'] = df['close'].shift(1)
        df['prev_upper'] = df['upper'].shift(1)
        df['prev_lower'] = df['lower'].shift(1)
        
        # 价格由下方突破下轨，买入信号
        buy_signal = (df['close'] >= df['lower']) & (df['prev_close'] < df['prev_lower'])
        df.loc[buy_signal, 'signal'] = 1
        
        # 记录买入信号触发原因
        for idx in df.index[buy_signal]:
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            reason = f"买入信号触发 [{date_str}]: 价格从下方突破布林带下轨, " \
                    f"收盘价: {df.loc[idx, 'close']:.2f}, " \
                    f"下轨: {df.loc[idx, 'lower']:.2f}, " \
                    f"昨日收盘价: {df.loc[idx, 'prev_close']:.2f}, " \
                    f"昨日下轨: {df.loc[idx, 'prev_lower']:.2f}"
            logger.info(reason)
            # 添加触发原因到信号数据中
            df.loc[idx, 'trigger_reason'] = f"价格从下方突破布林带下轨（{window}日，{num_std}倍标准差）"
        
        # 价格由上方突破上轨，卖出信号
        sell_signal = (df['close'] <= df['upper']) & (df['prev_close'] > df['prev_upper'])
        df.loc[sell_signal, 'signal'] = -1
        
        # 记录卖出信号触发原因
        for idx in df.index[sell_signal]:
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            reason = f"卖出信号触发 [{date_str}]: 价格从上方突破布林带上轨, " \
                    f"收盘价: {df.loc[idx, 'close']:.2f}, " \
                    f"上轨: {df.loc[idx, 'upper']:.2f}, " \
                    f"昨日收盘价: {df.loc[idx, 'prev_close']:.2f}, " \
                    f"昨日上轨: {df.loc[idx, 'prev_upper']:.2f}"
            logger.info(reason)
            # 添加触发原因到信号数据中
            df.loc[idx, 'trigger_reason'] = f"价格从上方突破布林带上轨（{window}日，{num_std}倍标准差）"
        
        # 持仓信号：根据价格与布林带的相对位置判断
        df['position'] = 0
        df.loc[df['close'] < df['middle'], 'position'] = 1  # 价格低于中轨，建议持有多仓
        df.loc[df['close'] > df['middle'], 'position'] = -1  # 价格高于中轨，建议持有空仓
        
        # 添加其他必要的信息
        df['symbol'] = df['symbol'] if 'symbol' in df.columns else self.data['symbol'].iloc[0] if 'symbol' in self.data.columns else 'default'
        
        # 统计买入和卖出信号数量
        buy_signals = (df['signal'] == 1).sum()
        sell_signals = (df['signal'] == -1).sum()
        logger.info(f"生成信号完成 - 买入信号: {buy_signals}个, 卖出信号: {sell_signals}个")
        
        return df

class MACDStrategy(StrategyBase):
    """MACD策略"""
    
    def __init__(self, parameters=None):
        """
        初始化策略
        
        Args:
            parameters (dict, optional): 策略参数
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 参数类型检查
        if parameters is not None and not isinstance(parameters, dict):
            logger.error(f"MACDStrategy.__init__: parameters参数类型错误，期望dict，实际为{type(parameters)}")
            parameters = {}  # 重置为空字典以避免后续错误
            
        default_params = {
            'fast_period': 12,      # 快速EMA周期
            'slow_period': 26,      # 慢速EMA周期
            'signal_period': 9,     # 信号线周期
            'commission_rate': 0.0003  # 手续费率
        }
        
        if parameters:
            default_params.update(parameters)
            
        # 调用父类初始化方法
        super().__init__(default_params, "MACD策略")
    
    def generate_signals(self, data: pd.DataFrame = None):
        """
        生成交易信号
        
        Args:
            data: 可选，包含价格数据的DataFrame，如果为None则使用self.data
            
        Returns:
            pandas.DataFrame: 包含交易信号的DataFrame
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 如果提供了data参数，使用它；否则使用self.data
        if data is None:
            data = self.data
            
        if data is None or data.empty:
            logger.error("没有数据可生成信号")
            return pd.DataFrame()
            
        df = data.copy()
        
        # 参数获取
        fast_period = int(self.parameters.get('fast_period', 12))
        slow_period = int(self.parameters.get('slow_period', 26))
        signal_period = int(self.parameters.get('signal_period', 9))
        
        logger.info(f"生成MACD信号 - 快速: {fast_period}, 慢速: {slow_period}, 信号: {signal_period}")
        
        # 计算MACD指标
        df['ema_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 初始化信号列
        df['signal'] = 0
        
        # 计算前一天的MACD直方图
        df['prev_hist'] = df['macd_hist'].shift(1)
        
        # MACD直方图由负转正，买入信号（金叉）
        golden_cross = (df['macd_hist'] > 0) & (df['prev_hist'] <= 0)
        df.loc[golden_cross, 'signal'] = 1
        
        # 记录买入信号触发原因
        for idx in df.index[golden_cross]:
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            reason = f"买入信号触发 [{date_str}]: MACD金叉, " \
                    f"MACD: {df.loc[idx, 'macd']:.4f}, " \
                    f"信号线: {df.loc[idx, 'macd_signal']:.4f}, " \
                    f"MACD柱状图: {df.loc[idx, 'macd_hist']:.4f}, " \
                    f"昨日柱状图: {df.loc[idx, 'prev_hist']:.4f}, " \
                    f"收盘价: {df.loc[idx, 'close']:.2f}"
            logger.info(reason)
            # 添加触发原因到信号数据中
            df.loc[idx, 'trigger_reason'] = f"MACD金叉（快速期: {fast_period}, 慢速期: {slow_period}, 信号期: {signal_period}）"
        
        # MACD直方图由正转负，卖出信号（死叉）
        death_cross = (df['macd_hist'] < 0) & (df['prev_hist'] >= 0)
        df.loc[death_cross, 'signal'] = -1
        
        # 记录卖出信号触发原因
        for idx in df.index[death_cross]:
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            reason = f"卖出信号触发 [{date_str}]: MACD死叉, " \
                    f"MACD: {df.loc[idx, 'macd']:.4f}, " \
                    f"信号线: {df.loc[idx, 'macd_signal']:.4f}, " \
                    f"MACD柱状图: {df.loc[idx, 'macd_hist']:.4f}, " \
                    f"昨日柱状图: {df.loc[idx, 'prev_hist']:.4f}, " \
                    f"收盘价: {df.loc[idx, 'close']:.2f}"
            logger.info(reason)
            # 添加触发原因到信号数据中
            df.loc[idx, 'trigger_reason'] = f"MACD死叉（快速期: {fast_period}, 慢速期: {slow_period}, 信号期: {signal_period}）"
        
        # 持仓信号：根据MACD与信号线的相对位置判断
        df['position'] = 0
        df.loc[df['macd'] > df['macd_signal'], 'position'] = 1  # MACD在信号线之上，建议持有多仓
        df.loc[df['macd'] < df['macd_signal'], 'position'] = -1  # MACD在信号线之下，建议持有空仓
        
        # 添加其他必要的信息
        df['symbol'] = df['symbol'] if 'symbol' in df.columns else self.data['symbol'].iloc[0] if 'symbol' in self.data.columns else 'default'
        
        # 统计买入和卖出信号数量
        buy_signals = (df['signal'] == 1).sum()
        sell_signals = (df['signal'] == -1).sum()
        logger.info(f"生成信号完成 - 买入信号: {buy_signals}个, 卖出信号: {sell_signals}个")
        
        return df

class RSIStrategy(StrategyBase):
    """RSI策略"""
    
    def __init__(self, parameters=None):
        """
        初始化策略
        
        Args:
            parameters (dict, optional): 策略参数
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 参数类型检查
        if parameters is not None and not isinstance(parameters, dict):
            logger.error(f"RSIStrategy.__init__: parameters参数类型错误，期望dict，实际为{type(parameters)}")
            parameters = {}  # 重置为空字典以避免后续错误
            
        default_params = {
            'rsi_period': 14,      # RSI周期
            'overbought': 70,      # 超买阈值
            'oversold': 30,        # 超卖阈值
            'commission_rate': 0.0003  # 手续费率
        }
        
        if parameters:
            default_params.update(parameters)
            
        # 调用父类初始化方法
        super().__init__(default_params, "RSI策略")
    
    def generate_signals(self, data: pd.DataFrame = None):
        """
        生成交易信号
        
        Args:
            data: 可选，包含价格数据的DataFrame，如果为None则使用self.data
            
        Returns:
            pandas.DataFrame: 包含交易信号的DataFrame
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 如果提供了data参数，使用它；否则使用self.data
        if data is None:
            data = self.data
            
        if data is None or data.empty:
            logger.error("没有数据可生成信号")
            return pd.DataFrame()
            
        df = data.copy()
        
        # 参数获取
        rsi_period = int(self.parameters.get('rsi_period', 14))
        overbought = float(self.parameters.get('overbought', 70))
        oversold = float(self.parameters.get('oversold', 30))
        
        logger.info(f"生成RSI信号 - 周期: {rsi_period}, 超买阈值: {overbought}, 超卖阈值: {oversold}")
        
        # 计算RSI指标
        df['price_change'] = df['close'].diff()
        df['gain'] = df['price_change'].clip(lower=0)
        df['loss'] = -df['price_change'].clip(upper=0)
        df['avg_gain'] = df['gain'].rolling(window=rsi_period, min_periods=1).mean()
        df['avg_loss'] = df['loss'].rolling(window=rsi_period, min_periods=1).mean()
        
        # 避免除以零
        df['avg_loss'] = df['avg_loss'].replace(0, 0.00001)
        
        # 计算RSI
        df['rs'] = df['avg_gain'] / df['avg_loss']
        df['rsi'] = 100 - (100 / (1 + df['rs']))
        
        # 初始化信号列
        df['signal'] = 0
        
        # 计算前一天的RSI
        df['prev_rsi'] = df['rsi'].shift(1)
        
        # RSI从超卖区上穿，买入信号
        buy_signal = (df['rsi'] > oversold) & (df['prev_rsi'] <= oversold)
        df.loc[buy_signal, 'signal'] = 1
        
        # 记录买入信号触发原因
        for idx in df.index[buy_signal]:
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            reason = f"买入信号触发 [{date_str}]: RSI从超卖区上穿, " \
                    f"RSI: {df.loc[idx, 'rsi']:.2f}, " \
                    f"昨日RSI: {df.loc[idx, 'prev_rsi']:.2f}, " \
                    f"超卖阈值: {oversold}, " \
                    f"收盘价: {df.loc[idx, 'close']:.2f}"
            logger.info(reason)
            # 添加触发原因到信号数据中
            df.loc[idx, 'trigger_reason'] = f"RSI({rsi_period}日)从超卖区({oversold})上穿"
        
        # RSI从超买区下穿，卖出信号
        sell_signal = (df['rsi'] < overbought) & (df['prev_rsi'] >= overbought)
        df.loc[sell_signal, 'signal'] = -1
        
        # 记录卖出信号触发原因
        for idx in df.index[sell_signal]:
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            reason = f"卖出信号触发 [{date_str}]: RSI从超买区下穿, " \
                    f"RSI: {df.loc[idx, 'rsi']:.2f}, " \
                    f"昨日RSI: {df.loc[idx, 'prev_rsi']:.2f}, " \
                    f"超买阈值: {overbought}, " \
                    f"收盘价: {df.loc[idx, 'close']:.2f}"
            logger.info(reason)
            # 添加触发原因到信号数据中
            df.loc[idx, 'trigger_reason'] = f"RSI({rsi_period}日)从超买区({overbought})下穿"
        
        # 持仓信号：根据RSI值判断
        df['position'] = 0
        df.loc[df['rsi'] < 50, 'position'] = 1  # RSI低于50，建议持有多仓
        df.loc[df['rsi'] > 50, 'position'] = -1  # RSI高于50，建议持有空仓
        
        # 添加其他必要的信息
        df['symbol'] = df['symbol'] if 'symbol' in df.columns else self.data['symbol'].iloc[0] if 'symbol' in self.data.columns else 'default'
        
        # 统计买入和卖出信号数量
        buy_signals = (df['signal'] == 1).sum()
        sell_signals = (df['signal'] == -1).sum()
        logger.info(f"生成信号完成 - 买入信号: {buy_signals}个, 卖出信号: {sell_signals}个")
        
        return df 