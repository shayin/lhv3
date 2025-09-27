# 极大极小值策略v2版 - 修正未来数据问题
# 保持原始策略的所有功能和设计，只修正使用未来数据的问题
from .strategy_template import StrategyTemplate
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ExtremumStrategyV2(StrategyTemplate):
    """
    极大极小值策略v2版 - 修正未来数据问题
    
    保持原始策略的所有功能和设计：
    - 使用scipy.signal.argrelextrema进行高效的极值点识别
    - 分批交易参数
    - 风险控制参数
    - 信号强度计算参数
    - 性能优化参数
    
    修正的问题：
    - 不使用未来数据，改为滚动窗口方式识别极值
    - 每个时间点只能使用该时间点及之前的数据
    """
    
    def __init__(self, name="极大极小值策略v2版", data=None, parameters=None):
        """初始化策略"""
        default_params = {
            # 极值点识别参数
            "min_reversal_points": 5,      # 确认极值需要的最少连续反转点数
            "lookback_period": 10,         # 寻找极值的回望周期
            "min_price_change": 0.05,       # 最小价格变化幅度(5%)
            "signal_strength_threshold": 0.6,  # 信号强度阈值
            "max_trading_range": 3,        # 限制在极值点附近的最大交易范围(天)
            
            # 分批交易参数
            "batch_count": 4,              # 分批建仓的批次数
            "batch_interval": 3,            # 分批建仓的间隔天数
            "position_size_per_batch": 0.25, # 每批建仓的仓位比例(25%)
            
            # 风险控制参数
            "stop_loss_ratio": 0.1,        # 止损比例(10%)
            "take_profit_ratio": 0.2,      # 止盈比例(20%)
            "max_position_ratio": 1.0,      # 最大仓位比例(100%)
            
            # 信号强度计算参数
            "rsi_oversold": 30,            # RSI超卖阈值
            "rsi_overbought": 70,          # RSI超买阈值
            "volume_threshold": 1.5,       # 成交量放大阈值
            
            # 性能优化参数
            "max_extremums": 50,           # 最大极值点数量限制
            "min_extremum_distance": 5,    # 极值点之间的最小距离
        }
        
        # 合并用户参数与默认参数
        if parameters:
            default_params.update(parameters)
            
        super().__init__(name=name, data=data, parameters=default_params)
        
        # 策略状态
        self.current_position = 0.0
        self.entry_price = 0.0
        self.batch_entries = []
        self.last_buy_idx = None
        self.last_sell_idx = None
        self.processed_extremums = set()
        self.batch_stage = 0
        self.max_batch_stage = 0
        
    def find_extremums_rolling(self, prices, current_idx):
        """
        使用滚动窗口方式识别极值点 - 修正版，不使用未来数据
        优化版本：检查历史数据中的极值点，但不使用未来数据
        
        Args:
            prices: 价格序列
            current_idx: 当前时间点索引
            
        Returns:
            (minima_indices, maxima_indices): 极小值和极大值索引列表
        """
        try:
            lookback = self.parameters["lookback_period"]
            min_distance = self.parameters["min_extremum_distance"]
            min_change = self.parameters["min_price_change"]
            
            # 只使用当前时间点及之前的数据
            available_data = prices.iloc[:current_idx + 1]
            
            if len(available_data) < lookback * 2:
                return [], []
            
            minima_indices = []
            maxima_indices = []
            
            # 检查历史数据中的极值点（不包括当前点，因为当前点不能确认是否为极值）
            for i in range(lookback, len(available_data) - lookback):
                current_price = available_data.iloc[i]
                
                # 检查是否为极小值
                left_prices = available_data.iloc[i - lookback:i]
                right_prices = available_data.iloc[i + 1:i + lookback + 1]
                
                if (current_price <= left_prices.min() and 
                    current_price <= right_prices.min()):
                    # 检查价格变化幅度
                    price_change = max(
                        (right_prices.max() - current_price) / current_price,
                        (left_prices.max() - current_price) / current_price
                    )
                    if price_change >= min_change:
                        minima_indices.append(i)
                
                # 检查是否为极大值
                if (current_price >= left_prices.max() and 
                    current_price >= right_prices.max()):
                    price_change = max(
                        (current_price - right_prices.min()) / right_prices.min(),
                        (current_price - left_prices.min()) / left_prices.min()
                    )
                    if price_change >= min_change:
                        maxima_indices.append(i)
            
            # 过滤极值点，确保它们之间有足够的距离
            minima_indices = self._filter_extremums_by_distance(minima_indices, min_distance)
            maxima_indices = self._filter_extremums_by_distance(maxima_indices, min_distance)
            
            # 限制极值点数量，避免过多计算
            max_extremums = self.parameters["max_extremums"]
            if len(minima_indices) > max_extremums:
                minima_indices = self._select_best_extremums(
                    available_data, minima_indices, max_extremums, 'min'
                )
            if len(maxima_indices) > max_extremums:
                maxima_indices = self._select_best_extremums(
                    available_data, maxima_indices, max_extremums, 'max'
                )
            
            return minima_indices, maxima_indices
            
        except Exception as e:
            logger.warning(f"滚动窗口极值点识别失败: {e}")
            return [], []
    
    def _filter_extremums_by_distance(self, extremum_indices, min_distance):
        """过滤极值点，确保它们之间有足够的距离"""
        if len(extremum_indices) == 0:
            return extremum_indices
            
        filtered = [extremum_indices[0]]
        for idx in extremum_indices[1:]:
            if idx - filtered[-1] >= min_distance:
                filtered.append(idx)
                
        return np.array(filtered)
    
    def _select_best_extremums(self, prices, extremum_indices, max_count, extremum_type):
        """选择最佳的极值点，基于价格变化幅度"""
        if len(extremum_indices) <= max_count:
            return extremum_indices
            
        # 计算每个极值点的价格变化幅度
        price_changes = []
        for idx in extremum_indices:
            if extremum_type == 'min':
                # 对于极小值，计算从左侧最高点到右侧最高点的变化
                left_start = max(0, idx - self.parameters["lookback_period"])
                right_end = min(len(prices), idx + self.parameters["lookback_period"] + 1)
                left_max = prices.iloc[left_start:idx].max()
                right_max = prices.iloc[idx+1:right_end].max()
                price_change = max(
                    right_max - prices.iloc[idx], 
                    left_max - prices.iloc[idx]
                ) / prices.iloc[idx]
            else:
                # 对于极大值，计算从左侧最低点到右侧最低点的变化
                left_start = max(0, idx - self.parameters["lookback_period"])
                right_end = min(len(prices), idx + self.parameters["lookback_period"] + 1)
                left_min = prices.iloc[left_start:idx].min()
                right_min = prices.iloc[idx+1:right_end].min()
                price_change = max(
                    prices.iloc[idx] - right_min, 
                    prices.iloc[idx] - left_min
                ) / prices.iloc[idx]
                
            price_changes.append(price_change)
            
        # 选择价格变化最大的极值点
        sorted_indices = np.argsort(price_changes)[::-1]  # 降序排列
        return extremum_indices[sorted_indices[:max_count]]
    
    def calculate_signal_strength_optimized(self, current_idx, extremum_idx, prices, df):
        """优化的信号强度计算"""
        if extremum_idx >= len(prices):
            return 0.0
            
        max_range = self.parameters["max_trading_range"]
        time_distance = abs(current_idx - extremum_idx)
        
        if time_distance > max_range:
            return 0.0
            
        # 简化的信号强度计算
        base_strength = max(0, 1 - time_distance / max_range)
        
        # 只使用RSI进行信号强度调整，减少计算量
        rsi_strength = 0.0
        if 'rsi_14' in df.columns and current_idx < len(df):
            rsi_value = df.iloc[current_idx]['rsi_14']
            if not pd.isna(rsi_value):
                if extremum_idx in self.minima_indices:  # 极小值点
                    rsi_strength = max(0, (self.parameters["rsi_oversold"] - rsi_value) / self.parameters["rsi_oversold"])
                else:  # 极大值点
                    rsi_strength = max(0, (rsi_value - self.parameters["rsi_overbought"]) / (100 - self.parameters["rsi_overbought"]))
        
        # 简化的综合信号强度
        total_strength = base_strength * 0.7 + rsi_strength * 0.3
        return min(1.0, total_strength)
    
    def generate_signals(self):
        """
        生成交易信号 - v2版，修正未来数据问题
        
        主要修正：
        1. 不使用scipy.signal.argrelextrema的全局极值识别
        2. 改为滚动窗口方式，每个时间点只使用历史数据
        3. 保持原始策略的所有其他功能和参数
        """
        if self.data is None or self.data.empty:
            logger.warning("未设置数据或数据为空，无法生成信号")
            return pd.DataFrame()
            
        # 获取参数
        signal_threshold = self.parameters["signal_strength_threshold"]
        max_range = self.parameters["max_trading_range"]
        batch_size = self.parameters["position_size_per_batch"]
        stop_loss = self.parameters["stop_loss_ratio"]
        take_profit = self.parameters["take_profit_ratio"]
        
        logger.info(f"生成极大极小值信号v2版: 信号阈值={signal_threshold}")
        
        # 计算技术指标
        df = self.calculate_indicators()
        prices = df['close']
        
        # 初始化信号列
        df["signal"] = 0
        df["trigger_reason"] = ""
        df["signal_strength"] = 0.0
        
        # 初始化状态
        current_position = 0.0
        entry_price = 0.0
        batch_entries = []
        last_buy_idx = None
        last_sell_idx = None
        processed_extremums = set()
        batch_stage = 0
        
        # 遍历每个时间点生成信号（不使用未来数据）
        for i in range(len(df)):
            current_price = prices.iloc[i]
            signal = 0
            signal_strength = 0.0
            trigger_reason = ""
            
            # 使用滚动窗口方式识别极值点（不使用未来数据）
            self.minima_indices, self.maxima_indices = self.find_extremums_rolling(prices, i)
            
            # 检查止损止盈
            if current_position > 0 and entry_price > 0:
                if current_price <= entry_price * (1 - stop_loss):
                    signal = -1
                    signal_strength = 1.0
                    trigger_reason = f"止损: 价格{current_price:.2f}, 入场价{entry_price:.2f}"
                elif current_price >= entry_price * (1 + take_profit):
                    signal = -1
                    signal_strength = 1.0
                    trigger_reason = f"止盈: 价格{current_price:.2f}, 入场价{entry_price:.2f}"
            
            # 检查买入信号（极小值附近）
            if signal == 0 and current_position < self.parameters["max_position_ratio"]:
                for extremum_idx in self.minima_indices:
                    if extremum_idx not in processed_extremums:
                        strength = self.calculate_signal_strength_optimized(i, extremum_idx, prices, df)
                        
                        if strength > signal_threshold and (last_buy_idx is None or i - last_buy_idx >= self.parameters["batch_interval"]):
                            signal = 1
                            signal_strength = strength
                            trigger_reason = f"极小值买入: 强度{strength:.2f}, 距离极值点{abs(i - extremum_idx)}天"
                            processed_extremums.add(extremum_idx)
                            break
            
            # 检查卖出信号（极大值附近）
            if signal == 0 and current_position > 0:
                for extremum_idx in self.maxima_indices:
                    if extremum_idx not in processed_extremums:
                        strength = self.calculate_signal_strength_optimized(i, extremum_idx, prices, df)
                        
                        if strength > signal_threshold and (last_sell_idx is None or i - last_sell_idx >= self.parameters["batch_interval"]):
                            signal = -1
                            signal_strength = strength
                            trigger_reason = f"极大值卖出: 强度{strength:.2f}, 距离极值点{abs(i - extremum_idx)}天"
                            processed_extremums.add(extremum_idx)
                            break
            
            # 更新仓位状态
            if signal == 1:  # 买入
                if current_position < self.parameters["max_position_ratio"]:
                    remaining_position = self.parameters["max_position_ratio"] - current_position
                    buy_ratio = min(batch_size, remaining_position)
                    
                    current_position += buy_ratio
                    batch_entries.append(current_price)
                    last_buy_idx = i
                    batch_stage += 1
                    
                    trigger_reason += f" | 买入{buy_ratio:.1%}, 总仓位{current_position:.1%}"
                    
                    if entry_price == 0:
                        entry_price = current_price
                    else:
                        entry_price = np.mean(batch_entries)
                        
            elif signal == -1:  # 卖出
                if current_position > 0:
                    sell_ratio = min(batch_size, current_position)
                    current_position -= sell_ratio
                    last_sell_idx = i
                    batch_stage = max(0, batch_stage - 1)
                    
                    trigger_reason += f" | 卖出{sell_ratio:.1%}, 剩余仓位{current_position:.1%}"
                    
                    if current_position <= 0:
                        entry_price = 0.0
                        batch_entries = []
                        batch_stage = 0
            
            # 记录信号
            df.iloc[i, df.columns.get_loc('signal')] = signal
            df.iloc[i, df.columns.get_loc('trigger_reason')] = trigger_reason
            df.iloc[i, df.columns.get_loc('signal_strength')] = signal_strength
        
        # 统计信号
        buy_count = (df['signal'] == 1).sum()
        sell_count = (df['signal'] == -1).sum()
        logger.info(f"信号统计: 买入信号={buy_count}个, 卖出信号={sell_count}个")
        logger.info(f"处理的极值点数量: {len(processed_extremums)}")
        
        return df
