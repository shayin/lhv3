from .templates.strategy_template import StrategyTemplate
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ExtremumStrategyV8(StrategyTemplate):
    """
    极大极小值策略 v8 - 修正仓位管理版本
    
    基于V6策略，主要改进：
    1. 修正仓位管理问题：统一买入和卖出的仓位计算方式
    2. 买入时使用固定比例（相对于总资金）
    3. 卖出时也使用固定比例（相对于总资金），而不是相对于当前持仓
    4. 确保买入和卖出的仓位大小一致，避免卖出过少的问题
    
    主要特点：
    1. 多条件组合识别极值：
       - 均线下穿/上穿确认趋势转折
       - 价格从上涨转为下跌N个点（极大值）
       - 价格从下跌转为上涨N个点（极小值）
       - RSI超买/超卖区域确认
       - 成交量放大确认
    
    2. 动态参数调整：
       - 根据市场波动性调整识别阈值
       - 自适应仓位管理
       - 多级止损保护
    
    3. 严格避免未来数据：
       - 所有计算只使用当前及历史数据
       - 滚动窗口计算技术指标
    """

    def __init__(self, name="极大极小值策略v8", data=None, parameters=None):
        default_params = {
            # 极值识别基础参数
            "lookback_period": 12,              # 回望周期
            "min_price_change_pct": 0.03,       # 最小价格变化百分比
            "extremum_confirm_days": 3,         # 极值确认天数
            
            # 均线参数
            "ma_short": 10,                     # 短期均线
            "ma_long": 20,                      # 长期均线
            "ma_cross_confirm": True,           # 是否需要均线交叉确认
            
            # 趋势转折识别参数
            "trend_reversal_points": 5,         # 趋势转折点数（连续上涨/下跌天数）
            "reversal_threshold_pct": 0.02,     # 转折阈值百分比
            
            # RSI参数
            "rsi_period": 14,                   # RSI周期
            "rsi_overbought": 70,               # RSI超买线
            "rsi_oversold": 30,                 # RSI超卖线
            "rsi_confirm": True,                # 是否需要RSI确认
            
            # 成交量确认参数
            "volume_ma_period": 20,             # 成交量均线周期
            "volume_amplify_ratio": 1.5,        # 成交量放大倍数
            "volume_confirm": True,             # 是否需要成交量确认
            
            # 信号强度参数
            # V8修正：降低默认信号强度阈值，提高信号敏感度
        "signal_strength_threshold": 0.45,  # 从0.65降低到0.45  # 信号强度阈值
            "max_signals_per_period": 3,        # 每个周期最大信号数
            
            # 仓位管理参数 - V8修正版
            "base_position_size": 0.05,         # 基础仓位大小（统一买入卖出比例）
            "max_position_ratio": 0.8,          # 最大仓位比例
            "position_scaling": True,           # 是否启用仓位缩放
            
            # 风险控制参数
            "stop_loss_pct": 0.06,              # 止损百分比
            "take_profit_pct": 0.15,            # 止盈百分比
            "trailing_stop_pct": 0.04,          # 移动止损百分比
            "max_hold_days": 25,                # 最大持仓天数
            
            # 市场环境过滤
            "market_trend_period": 50,          # 市场趋势判断周期
            "bear_market_threshold": -0.1,      # 熊市阈值
            "bull_market_threshold": 0.1,       # 牛市阈值
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(name=name, data=data, parameters=default_params)

        # 策略状态变量
        self.current_position = 0.0
        self.entry_prices = []
        self.entry_dates = []
        self.processed_extremums = set()
        self.trailing_stop_price = None
        self.last_signal_date = None

    def calculate_indicators(self):
        """计算所有必要的技术指标"""
        df = super().calculate_indicators()
        
        # 短期和长期均线
        ma_short = self.parameters.get("ma_short", 10)
        ma_long = self.parameters.get("ma_long", 20)
        df[f'ma_{ma_short}'] = df['close'].rolling(window=ma_short, min_periods=1).mean()
        df[f'ma_{ma_long}'] = df['close'].rolling(window=ma_long, min_periods=1).mean()
        
        # 均线交叉信号
        df['ma_cross_bull'] = (df[f'ma_{ma_short}'] > df[f'ma_{ma_long}']) & \
                              (df[f'ma_{ma_short}'].shift(1) <= df[f'ma_{ma_long}'].shift(1))
        df['ma_cross_bear'] = (df[f'ma_{ma_short}'] < df[f'ma_{ma_long}']) & \
                              (df[f'ma_{ma_short}'].shift(1) >= df[f'ma_{ma_long}'].shift(1))
        
        # 成交量均线
        volume_ma_period = self.parameters.get("volume_ma_period", 20)
        df['volume_ma'] = df['volume'].rolling(window=volume_ma_period, min_periods=1).mean()
        # 防止除零错误：检查成交量均线是否为零
        df['volume_ratio'] = df['volume'] / df['volume_ma'].replace(0, 1e-9)
        
        # 价格变化率
        df['price_change_pct'] = df['close'].pct_change()
        df['price_change_cumsum'] = df['price_change_pct'].rolling(
            window=self.parameters.get("trend_reversal_points", 5)
        ).sum()
        
        # 市场趋势
        market_period = self.parameters.get("market_trend_period", 50)
        df['market_trend'] = df['close'].pct_change(periods=market_period)
        
        return df

    def identify_extremum_candidates(self, df, current_idx):
        """识别极值候选点"""
        if current_idx < self.parameters.get("lookback_period", 12):
            return [], []
            
        lookback = self.parameters.get("lookback_period", 12)
        confirm_days = self.parameters.get("extremum_confirm_days", 3)
        
        # 确保不使用未来数据
        end_idx = current_idx - confirm_days + 1
        if end_idx < lookback:
            return [], []
            
        minima_candidates = []
        maxima_candidates = []
        
        # 在可用数据范围内寻找极值
        for i in range(lookback, end_idx):
            current_price = df['close'].iloc[i]
            
            # 获取左右窗口数据
            left_window = df['close'].iloc[i-lookback:i]
            right_window = df['close'].iloc[i+1:i+confirm_days+1]
            
            if len(right_window) < confirm_days:
                continue
                
            # 极小值判断
            if (current_price <= left_window.min() and 
                current_price <= right_window.min()):
                
                # 计算价格变化幅度，防止除零错误
                if current_price == 0:
                    max_recovery = 0
                else:
                    max_recovery = max(
                        (right_window.max() - current_price) / current_price,
                        (left_window.max() - current_price) / current_price
                    )
                
                if max_recovery >= self.parameters.get("min_price_change_pct", 0.03):
                    minima_candidates.append(i)
            
            # 极大值判断
            if (current_price >= left_window.max() and 
                current_price >= right_window.max()):
                
                # 计算价格下跌幅度，防止除零错误
                if current_price == 0:
                    max_decline = 0
                else:
                    max_decline = max(
                        (current_price - right_window.min()) / current_price,
                        (current_price - left_window.min()) / current_price
                    )
                
                if max_decline >= self.parameters.get("min_price_change_pct", 0.03):
                    maxima_candidates.append(i)
        
        return minima_candidates, maxima_candidates

    def calculate_signal_strength(self, df, extremum_idx, extremum_type, current_idx):
        """计算信号强度（0-1之间）"""
        if extremum_idx >= len(df) or current_idx >= len(df):
            return 0.0
            
        strength = 0.0
        max_strength = 0.0
        
        # 1. 价格变化幅度强度 (权重: 0.3)
        price_change_weight = 0.3
        current_price = df['close'].iloc[current_idx]
        extremum_price = df['close'].iloc[extremum_idx]
        
        # 防止除零错误
        if extremum_price == 0 or pd.isna(extremum_price):
            price_change = 0
        else:
            if extremum_type == 'min':
                price_change = (current_price - extremum_price) / extremum_price
            else:
                price_change = (extremum_price - current_price) / extremum_price
            
        price_strength = min(1.0, abs(price_change) / 0.1)  # 10%变化为满分
        strength += price_strength * price_change_weight
        max_strength += price_change_weight
        
        # 2. 均线交叉确认强度 (权重: 0.25)
        if self.parameters.get("ma_cross_confirm", True):
            ma_weight = 0.25
            ma_short = self.parameters.get("ma_short", 10)
            ma_long = self.parameters.get("ma_long", 20)
            
            # V8修正：放宽均线确认条件
            if extremum_type == 'min':
                if df['ma_cross_bull'].iloc[current_idx]:
                    strength += ma_weight  # 金叉确认
                elif df[f'ma_{ma_short}'].iloc[current_idx] > df[f'ma_{ma_long}'].iloc[current_idx]:
                    strength += ma_weight * 0.5  # 短期均线在长期均线之上
            elif extremum_type == 'max':
                if df['ma_cross_bear'].iloc[current_idx]:
                    strength += ma_weight  # 死叉确认
                elif df[f'ma_{ma_short}'].iloc[current_idx] < df[f'ma_{ma_long}'].iloc[current_idx]:
                    strength += ma_weight * 0.5  # 短期均线在长期均线之下
                
            max_strength += ma_weight
        
        # 3. RSI确认强度 (权重: 0.2)
        if self.parameters.get("rsi_confirm", True):
            rsi_weight = 0.2
            current_rsi = df['rsi_14'].iloc[current_idx]
            
            # V8修正：放宽RSI确认条件
            if extremum_type == 'min':
                if current_rsi <= self.parameters.get("rsi_oversold", 30):
                    rsi_strength = (30 - current_rsi) / 30
                    strength += rsi_strength * rsi_weight
                elif current_rsi <= 50:  # RSI低于50也给予部分强度
                    rsi_strength = (50 - current_rsi) / 50 * 0.5
                    strength += rsi_strength * rsi_weight
            elif extremum_type == 'max':
                if current_rsi >= self.parameters.get("rsi_overbought", 70):
                    rsi_strength = (current_rsi - 70) / 30
                    strength += rsi_strength * rsi_weight
                elif current_rsi >= 50:  # RSI高于50也给予部分强度
                    rsi_strength = (current_rsi - 50) / 50 * 0.5
                    strength += rsi_strength * rsi_weight
                
            max_strength += rsi_weight
        
        # 4. 成交量确认强度 (权重: 0.15)
        if self.parameters.get("volume_confirm", True):
            volume_weight = 0.15
            volume_ratio = df['volume_ratio'].iloc[current_idx]
            min_ratio = self.parameters.get("volume_amplify_ratio", 1.5)
            
            if volume_ratio >= min_ratio:
                volume_strength = min(1.0, (volume_ratio - 1) / 2)  # 3倍成交量为满分
                strength += volume_strength * volume_weight
                
            max_strength += volume_weight
        
        # 5. 时间距离强度 (权重: 0.1)
        time_weight = 0.1
        time_distance = current_idx - extremum_idx
        max_distance = self.parameters.get("max_hold_days", 25)
        
        # 防止除零错误
        if max_distance > 0:
            time_strength = max(0, 1 - time_distance / max_distance)
        else:
            time_strength = 0
            
        strength += time_strength * time_weight
        max_strength += time_weight
        
        # 标准化强度值，防止除零错误
        if max_strength > 0:
            return min(1.0, strength / max_strength)
        else:
            return 0.0

    def check_market_environment(self, df, current_idx):
        """检查市场环境，过滤不适合的交易时机"""
        if current_idx < self.parameters.get("market_trend_period", 50):
            return True  # 数据不足时允许交易
            
        market_trend = df['market_trend'].iloc[current_idx]
        bear_threshold = self.parameters.get("bear_market_threshold", -0.1)
        bull_threshold = self.parameters.get("bull_market_threshold", 0.1)
        
        # 在极端熊市中谨慎买入
        if market_trend < bear_threshold:
            return False
            
        return True

    def calculate_position_size(self, signal_strength, current_position, signal_type='buy'):
        """
        V8修正版：统一买入和卖出的仓位计算方式
        
        Args:
            signal_strength: 信号强度
            current_position: 当前仓位
            signal_type: 信号类型 ('buy' 或 'sell')
        
        Returns:
            建议仓位大小
        """
        base_size = self.parameters.get("base_position_size", 0.05)
        max_position = self.parameters.get("max_position_ratio", 0.8)
        
        if not self.parameters.get("position_scaling", True):
            # 不启用仓位缩放时，使用固定仓位
            if signal_type == 'buy':
                available_position = max_position - current_position
                return min(base_size, available_position)
            else:  # sell
                # 卖出时也使用固定比例，而不是全部卖出
                return min(base_size, current_position)
        
        # 启用仓位缩放时，根据信号强度调整仓位
        scaled_size = base_size * signal_strength
        
        if signal_type == 'buy':
            # 买入时确保不超过最大仓位限制
            available_position = max_position - current_position
            return min(scaled_size, available_position)
        else:  # sell
            # 卖出时使用相同的计算方式，确保买卖仓位一致
            return min(scaled_size, current_position)

    def generate_signals(self):
        """生成交易信号"""
        if self.data is None or self.data.empty:
            logger.warning("未设置数据或数据为空，无法生成信号")
            return pd.DataFrame()

        df = self.calculate_indicators()
        
        # 初始化信号列
        df['signal'] = 0
        df['trigger_reason'] = ''
        df['signal_strength'] = 0.0
        df['position_size'] = 0.0

        current_position = 0.0
        entry_prices = []
        trailing_stop_price = None
        processed_extremums = set()

        for i in range(len(df)):
            current_price = df['close'].iloc[i]
            signal = 0
            signal_strength = 0.0
            trigger_reason = ''
            position_size = 0.0

            # 检查市场环境
            if not self.check_market_environment(df, i):
                df.iloc[i, df.columns.get_loc('signal')] = signal
                df.iloc[i, df.columns.get_loc('trigger_reason')] = '市场环境不适合交易'
                df.iloc[i, df.columns.get_loc('signal_strength')] = signal_strength
                df.iloc[i, df.columns.get_loc('position_size')] = position_size
                continue

            # 风险控制检查
            if current_position > 0 and len(entry_prices) > 0:
                avg_entry_price = np.mean(entry_prices)
                
                # 止损检查
                stop_loss_price = avg_entry_price * (1 - self.parameters.get("stop_loss_pct", 0.06))
                if current_price <= stop_loss_price:
                    signal = -1
                    trigger_reason = f"止损触发: 当前价{current_price:.2f}, 止损价{stop_loss_price:.2f}"
                    position_size = current_position  # 止损时全部卖出
                
                # 止盈检查
                elif current_price >= avg_entry_price * (1 + self.parameters.get("take_profit_pct", 0.15)):
                    signal = -1
                    trigger_reason = f"止盈触发: 当前价{current_price:.2f}, 入场均价{avg_entry_price:.2f}"
                    position_size = current_position  # 止盈时全部卖出
                
                # 移动止损检查
                elif trailing_stop_price is not None and current_price <= trailing_stop_price:
                    signal = -1
                    trigger_reason = f"移动止损触发: 当前价{current_price:.2f}, 移动止损价{trailing_stop_price:.2f}"
                    position_size = current_position  # 移动止损时全部卖出
                
                # 更新移动止损价
                if signal == 0 and current_price > avg_entry_price:
                    new_trailing_stop = current_price * (1 - self.parameters.get("trailing_stop_pct", 0.04))
                    if trailing_stop_price is None or new_trailing_stop > trailing_stop_price:
                        trailing_stop_price = new_trailing_stop

            # 如果没有风险控制信号，寻找交易机会
            if signal == 0:
                # 识别极值候选点
                minima_candidates, maxima_candidates = self.identify_extremum_candidates(df, i)
                
                # 检查买入信号（极小值）
                if current_position < self.parameters.get("max_position_ratio", 0.8):
                    for extremum_idx in minima_candidates:
                        if extremum_idx not in processed_extremums:
                            strength = self.calculate_signal_strength(df, extremum_idx, 'min', i)
                            
                            if strength >= self.parameters.get("signal_strength_threshold", 0.65):
                                signal = 1
                                signal_strength = strength
                                position_size = self.calculate_position_size(strength, current_position, 'buy')
                                trigger_reason = f"极小值买入: 强度{strength:.2f}, 极值位置{extremum_idx}, 买入比例{self.parameters.get('base_position_size', 0.05):.1%}"
                                processed_extremums.add(extremum_idx)
                                break
                
                # 检查卖出信号（极大值）
                # V8修正：即使没有仓位也可以生成卖出信号（用于分析）
                if signal == 0:
                    for extremum_idx in maxima_candidates:
                        if extremum_idx not in processed_extremums:
                            strength = self.calculate_signal_strength(df, extremum_idx, 'max', i)
                            
                            if strength >= self.parameters.get("signal_strength_threshold", 0.65):
                                signal = -1
                                signal_strength = strength
                                # V8修正：使用统一的仓位计算方式
                                if current_position > 0:
                                    position_size = self.calculate_position_size(strength, current_position, 'sell')
                                else:
                                    # 没有仓位时，记录信号但仓位为0
                                    position_size = 0.0
                                trigger_reason = f"极大值卖出: 强度{strength:.2f}, 极值位置{extremum_idx}, 卖出比例{self.parameters.get('base_position_size', 0.05):.1%}"
                                processed_extremums.add(extremum_idx)
                                break

            # 更新仓位状态
            if signal == 1 and position_size > 0:
                current_position += position_size
                entry_prices.append(current_price)
                if trailing_stop_price is None:
                    trailing_stop_price = current_price * (1 - self.parameters.get("trailing_stop_pct", 0.04))
                    
            elif signal == -1 and position_size > 0:
                # V8修正：支持部分卖出
                current_position -= position_size
                if current_position <= 0:
                    current_position = 0.0
                    entry_prices = []
                    trailing_stop_price = None
                else:
                    # 部分卖出时，按比例调整入场价格记录
                    remaining_ratio = current_position / (current_position + position_size)
                    entry_prices = entry_prices[:int(len(entry_prices) * remaining_ratio)]
            elif signal == -1 and position_size == 0:
                # V8修正：记录卖出信号但没有实际交易
                pass  # 保持当前仓位状态不变

            # 记录信号
            df.iloc[i, df.columns.get_loc('signal')] = signal
            df.iloc[i, df.columns.get_loc('trigger_reason')] = trigger_reason
            df.iloc[i, df.columns.get_loc('signal_strength')] = signal_strength
            df.iloc[i, df.columns.get_loc('position_size')] = position_size

        return df