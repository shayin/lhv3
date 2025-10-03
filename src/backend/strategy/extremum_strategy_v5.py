from .strategy_template import StrategyTemplate
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ExtremumStrategyV5(StrategyTemplate):
    """
    极大极小值策略 v5 - 在 v2 基础上增强下跌期防护与上涨期表现

    主要改进点：
    - 趋势过滤：使用长期移动平均确认上升/下降趋势，仅在顺势方向参与买入/卖出
    - ATR 自适应仓位：根据近期波动性（ATR）调整每次建仓大小，波动大时减仓
    - 分批建仓（batch）与分批买入间隔
    - 移动止损（trailing stop）：在获利时保护收益
    - 保留 v2 的滚动极值识别与信号强度计算
    """

    def __init__(self, name="极大极小值策略v5", data=None, parameters=None):
        default_params = {
            # 极值识别（复用 v2 的思路）
            "lookback_period": 10,
            "min_price_change": 0.05,
            "max_extremums": 50,
            "min_extremum_distance": 5,

            # 分批交易
            "batch_count": 4,
            "batch_interval": 3,
            "position_size_per_batch": 0.25,

            # 风险与止损
            "stop_loss_ratio": 0.08,       # 初始止损
            "trailing_stop_pct": 0.05,     # 移动止损百分比
            "take_profit_ratio": 0.18,
            "max_position_ratio": 1.0,

            # 趋势过滤
            "trend_ma_long": 60,           # 用于判断长期趋势的移动平均
            "require_trend": True,         # 是否启用趋势过滤

            # ATR 自适应仓位
            "atr_period": 14,
            "atr_sizing_factor": 0.5,      # ATR越大，每批仓位越小（乘子）

            # 信号强度/阈值
            "signal_strength_threshold": 0.6,

            # 性能限额
            "max_hold_days": 30,
        }

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
        self.trailing_stop_price = None

    def calculate_indicators(self):
        """计算必要的技术指标：MA, ATR 等"""
        df = super().calculate_indicators()

        # 长期趋势均线
        ma_long = self.parameters.get("trend_ma_long", 60)
        df[f'ma_{ma_long}'] = df['close'].rolling(window=ma_long, min_periods=1).mean()

        # ATR
        atr_period = self.parameters.get("atr_period", 14)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=atr_period, min_periods=1).mean()

        return df

    def in_uptrend(self, idx, df):
        if not self.parameters.get('require_trend', True):
            return True

        ma_long = self.parameters.get('trend_ma_long', 60)
        if idx < ma_long:
            return True

        return df['close'].iloc[idx] > df[f'ma_{ma_long}'].iloc[idx]

    def adaptive_batch_size(self, idx, df):
        """根据 ATR 动态调整每批仓位（返回比例，例如 0.25 表示 25%）"""
        base = self.parameters.get('position_size_per_batch', 0.25)
        atr = df['atr'].iloc[idx] if 'atr' in df.columns and idx < len(df) else None
        if atr is None or atr == 0:
            return base

        factor = self.parameters.get('atr_sizing_factor', 0.5)
        # ATR 越高，减小仓位。简单归一化：1/(1+atr*factor)
        adj = 1.0 / (1.0 + atr * factor)
        # 保持在 [0.1, base]
        size = max(0.05, min(base, base * adj))
        return size

    def find_extremums_rolling(self, prices, current_idx):
        """
        使用 v2 的滚动窗口极值识别逻辑（不使用未来数据）
        """
        try:
            lookback = self.parameters.get("lookback_period", 10)
            min_distance = self.parameters.get("min_extremum_distance", 5)
            min_change = self.parameters.get("min_price_change", 0.05)

            available_data = prices.iloc[:current_idx + 1]
            if len(available_data) < lookback * 2:
                return [], []

            minima_indices = []
            maxima_indices = []

            for i in range(lookback, len(available_data) - lookback):
                current_price = available_data.iloc[i]
                left_prices = available_data.iloc[i - lookback:i]
                right_prices = available_data.iloc[i + 1:i + lookback + 1]

                # 极小值
                if (current_price <= left_prices.min() and current_price <= right_prices.min()):
                    price_change = max(
                        (right_prices.max() - current_price) / current_price,
                        (left_prices.max() - current_price) / current_price
                    )
                    if price_change >= min_change:
                        minima_indices.append(i)

                # 极大值
                if (current_price >= left_prices.max() and current_price >= right_prices.max()):
                    price_change = max(
                        (current_price - right_prices.min()) / right_prices.min(),
                        (current_price - left_prices.min()) / left_prices.min()
                    )
                    if price_change >= min_change:
                        maxima_indices.append(i)

            minima_indices = self._filter_extremums_by_distance(minima_indices, min_distance)
            maxima_indices = self._filter_extremums_by_distance(maxima_indices, min_distance)

            max_extremums = self.parameters.get("max_extremums", 50)
            if len(minima_indices) > max_extremums:
                minima_indices = self._select_best_extremums(available_data, minima_indices, max_extremums, 'min')
            if len(maxima_indices) > max_extremums:
                maxima_indices = self._select_best_extremums(available_data, maxima_indices, max_extremums, 'max')

            return minima_indices, maxima_indices
        except Exception as e:
            logger.warning(f"滚动窗口极值点识别失败(v5): {e}")
            return [], []

    def calculate_signal_strength_optimized(self, current_idx, extremum_idx, prices, df):
        # 复用 v2 的方法（如果存在）
        try:
            return super().calculate_signal_strength_optimized(current_idx, extremum_idx, prices, df)
        except Exception:
            # 简化：根据距离和价格差比例计算强度
            time_distance = abs(current_idx - extremum_idx)
            max_range = self.parameters.get('max_hold_days', 30)
            base_strength = max(0, 1 - time_distance / max_range)
            return min(1.0, base_strength)

    def _filter_extremums_by_distance(self, extremum_indices, min_distance):
        """过滤极值点，确保它们之间有足够的距离（从 v2 复制）"""
        try:
            if len(extremum_indices) == 0:
                return extremum_indices

            filtered = [extremum_indices[0]]
            for idx in extremum_indices[1:]:
                if idx - filtered[-1] >= min_distance:
                    filtered.append(idx)
            return np.array(filtered)
        except Exception:
            return []

    def _select_best_extremums(self, prices, extremum_indices, max_count, extremum_type):
        """选择价格变化幅度最大的极值点（从 v2 复制）"""
        try:
            if len(extremum_indices) <= max_count:
                return extremum_indices

            price_changes = []
            for idx in extremum_indices:
                if extremum_type == 'min':
                    left_start = max(0, idx - self.parameters.get("lookback_period", 10))
                    right_end = min(len(prices), idx + self.parameters.get("lookback_period", 10) + 1)
                    left_max = prices.iloc[left_start:idx].max()
                    right_max = prices.iloc[idx+1:right_end].max()
                    price_change = max(right_max - prices.iloc[idx], left_max - prices.iloc[idx]) / prices.iloc[idx]
                else:
                    left_start = max(0, idx - self.parameters.get("lookback_period", 10))
                    right_end = min(len(prices), idx + self.parameters.get("lookback_period", 10) + 1)
                    left_min = prices.iloc[left_start:idx].min()
                    right_min = prices.iloc[idx+1:right_end].min()
                    price_change = max(prices.iloc[idx] - right_min, prices.iloc[idx] - left_min) / prices.iloc[idx]
                price_changes.append(price_change)

            sorted_indices = np.argsort(price_changes)[::-1]
            return extremum_indices[sorted_indices[:max_count]]
        except Exception:
            return extremum_indices

    def generate_signals(self):
        if self.data is None or self.data.empty:
            logger.warning("未设置数据或数据为空，无法生成信号")
            return pd.DataFrame()

        df = self.calculate_indicators()
        prices = df['close']

        df['signal'] = 0
        df['trigger_reason'] = ''
        df['signal_strength'] = 0.0
        # 添加 position_size 列，回测引擎优先使用该值作为本次交易的仓位比例
        df['position_size'] = 0.0

        current_position = 0.0
        entry_price = 0.0
        batch_entries = []
        processed_extremums = set()
        last_buy_idx = None
        last_sell_idx = None

        for i in range(len(df)):
            current_price = prices.iloc[i]
            signal = 0
            signal_strength = 0.0
            trigger_reason = ''

            # 趋势过滤
            if not self.in_uptrend(i, df):
                # 非上升趋势时，谨慎买入；仍允许卖出平仓
                allow_buy = False
            else:
                allow_buy = True

            # 计算极值
            try:
                self.minima_indices, self.maxima_indices = self.find_extremums_rolling(prices, i)
            except Exception:
                self.minima_indices, self.maxima_indices = [], []

            # 检查止损/移动止损/止盈
            if current_position > 0 and entry_price > 0:
                # 更新 trailing stop
                if self.trailing_stop_price is None and current_price > entry_price:
                    self.trailing_stop_price = current_price * (1 - self.parameters.get('trailing_stop_pct', 0.05))
                elif self.trailing_stop_price is not None and current_price > entry_price:
                    # 提高 trailing stop
                    self.trailing_stop_price = max(self.trailing_stop_price, current_price * (1 - self.parameters.get('trailing_stop_pct', 0.05)))

                # 触发移动止损或初始止损
                if self.trailing_stop_price is not None and current_price <= self.trailing_stop_price:
                    signal = -1
                    trigger_reason = f"移动止损触发: 当前价{current_price:.2f}, trailing={self.trailing_stop_price:.2f}"
                elif current_price <= entry_price * (1 - self.parameters.get('stop_loss_ratio', 0.08)):
                    signal = -1
                    trigger_reason = f"止损触发: 当前价{current_price:.2f}, 入场{entry_price:.2f}"
                elif current_price >= entry_price * (1 + self.parameters.get('take_profit_ratio', 0.18)):
                    signal = -1
                    trigger_reason = f"止盈触发: 当前价{current_price:.2f}, 入场{entry_price:.2f}"

            # 买入逻辑（仅在允许买入时）
            if signal == 0 and allow_buy and current_position < self.parameters.get('max_position_ratio', 1.0):
                for extremum_idx in self.minima_indices:
                    if extremum_idx not in processed_extremums:
                        strength = self.calculate_signal_strength_optimized(i, extremum_idx, prices, df)
                        if strength > self.parameters.get('signal_strength_threshold', 0.6):
                            # 计算自适应仓位
                            batch_size = self.adaptive_batch_size(i, df)
                            remaining = self.parameters.get('max_position_ratio', 1.0) - current_position
                            buy_ratio = min(batch_size, remaining)
                            if buy_ratio > 0:
                                signal = 1
                                signal_strength = strength
                                trigger_reason = f"极小值买入: 强度{strength:.2f}, 建仓{buy_ratio:.2%}"
                                # 将建议仓位写入signals表中，供引擎直接使用
                                try:
                                    df.at[df.index[i], 'position_size'] = buy_ratio
                                except Exception:
                                    pass
                                processed_extremums.add(extremum_idx)
                                break

            # 卖出逻辑
            if signal == 0 and current_position > 0:
                for extremum_idx in self.maxima_indices:
                    if extremum_idx not in processed_extremums:
                        strength = self.calculate_signal_strength_optimized(i, extremum_idx, prices, df)
                        if strength > self.parameters.get('signal_strength_threshold', 0.6):
                            signal = -1
                            signal_strength = strength
                            trigger_reason = f"极大值卖出: 强度{strength:.2f}"
                            # 卖出时写入当前持仓比例，供引擎使用
                            try:
                                df.at[df.index[i], 'position_size'] = current_position
                            except Exception:
                                pass
                            processed_extremums.add(extremum_idx)
                            break

            # 应用交易动作
            if signal == 1:
                # 计算本次入场比例
                batch = self.adaptive_batch_size(i, df)
                remaining = self.parameters.get('max_position_ratio', 1.0) - current_position
                to_buy = min(batch, remaining)
                if to_buy > 0:
                    # 再次在实际应用处写入position_size，确保信号表中的值一致
                    try:
                        df.at[df.index[i], 'position_size'] = to_buy
                    except Exception:
                        pass
                    current_position += to_buy
                    batch_entries.append(current_price)
                    if entry_price == 0:
                        entry_price = current_price
                    else:
                        entry_price = np.mean(batch_entries)
                    # reset trailing stop when new entry increases price
                    if current_price > entry_price:
                        self.trailing_stop_price = current_price * (1 - self.parameters.get('trailing_stop_pct', 0.05))

            elif signal == -1:
                if current_position > 0:
                    sell_ratio = min(self.parameters.get('position_size_per_batch', 0.25), current_position)
                    current_position -= sell_ratio
                    if current_position <= 0:
                        entry_price = 0.0
                        batch_entries = []
                        self.trailing_stop_price = None

            df.iloc[i, df.columns.get_loc('signal')] = signal
            df.iloc[i, df.columns.get_loc('trigger_reason')] = trigger_reason
            df.iloc[i, df.columns.get_loc('signal_strength')] = signal_strength

        return df
