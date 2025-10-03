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
            # 分批建仓相关参数
            "batch_count": 1,            # 建仓批次数, 1 表示一次性建仓
            "batch_interval_bars": 1,    # 批次之间的时间间隔，以bar数为单位
            # 可选: 指定每批的相对权重（列表或逗号分隔的字符串），若不指定则均分
            "batch_weights": None,
            # 可选：基于不同均线对的分批规则，优先级高于 batch_* 参数
            # 格式示例（列表）：[{"short":3, "long":5, "weight":0.25}, {"short":5, "long":10, "weight":0.25}]
            # 或字符串："3-5:0.25,5-10:0.25"
            "cross_rules": None,
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
        # 每次信号可选地包含 position_size(0-1) 表示本次子单占总仓位的比例
        # 对于 cross_rules，我们会累加各规则给出的权重
        df['position_size'] = np.nan
        
        # 如果提供了 cross_rules，则按规则生成分批信号（每个规则指定 short/long/weight）
        cross_rules = self.parameters.get('cross_rules')
        rules = None
        if cross_rules is not None:
            # 解析多种格式
            if isinstance(cross_rules, str):
                # 例如: "3-5:0.25,5-10:0.25"
                try:
                    items = [s.strip() for s in cross_rules.split(',') if s.strip()]
                    parsed = []
                    for it in items:
                        pair, wt = it.split(':') if ':' in it else (it, None)
                        short_s, long_s = pair.split('-')
                        parsed.append({'short': int(short_s), 'long': int(long_s), 'weight': float(wt) if wt is not None else None})
                    rules = parsed
                except Exception:
                    rules = None
            elif isinstance(cross_rules, (list, tuple)):
                # assume list of dicts
                try:
                    parsed = []
                    for item in cross_rules:
                        s = int(item.get('short'))
                        l = int(item.get('long'))
                        w = item.get('weight', None)
                        parsed.append({'short': s, 'long': l, 'weight': float(w) if w is not None else None})
                    rules = parsed
                except Exception:
                    rules = None

        if rules:
            # 计算所有需要的MA
            windows = sorted({r['short'] for r in rules} | {r['long'] for r in rules})
            for w in windows:
                col = f'ma_{w}'
                if col not in df.columns:
                    df[col] = df['close'].rolling(window=w).mean()

            # 为每条规则生成信号并累加 position_size
            # 初始化 position_size 为 0.0 以便累加
            df['position_size'] = df['position_size'].fillna(0.0)

            for r in rules:
                s = r['short']
                l = r['long']
                wgt = r.get('weight') if r.get('weight') is not None else 0.0
                col_s = f'ma_{s}'
                col_l = f'ma_{l}'
                prev_s = df[col_s].shift(1)
                prev_l = df[col_l].shift(1)

                buy_mask = (df[col_s] > df[col_l]) & (prev_s <= prev_l)
                sell_mask = (df[col_s] < df[col_l]) & (prev_s >= prev_l)

                # 处理买信号：累加 position_size（若已有卖信号则不覆盖）
                for idx in df.index[buy_mask]:
                    if df.at[idx, 'signal'] == -1:
                        # 冲突：已有卖信号，不覆盖
                        continue
                    df.at[idx, 'signal'] = 1
                    prev_tr = df.at[idx, 'trigger_reason']
                    addition = f"MA{s}从下方上穿MA{l}"
                    df.at[idx, 'trigger_reason'] = (prev_tr + ' | ' if prev_tr else '') + addition
                    try:
                        df.at[idx, 'position_size'] = float(df.at[idx, 'position_size']) + float(wgt)
                    except Exception:
                        df.at[idx, 'position_size'] = float(wgt)

                # 处理卖信号：标记卖出（覆盖买入）
                df.loc[sell_mask, 'signal'] = -1
                for idx in df.index[sell_mask]:
                    prev_tr = df.at[idx, 'trigger_reason']
                    addition = f"MA{s}从上方下穿MA{l}"
                    df.at[idx, 'trigger_reason'] = (prev_tr + ' | ' if prev_tr else '') + addition

            # 限制 position_size 最大值为1
            df['position_size'] = df['position_size'].apply(lambda v: min(max(v, 0.0), 1.0) if not pd.isna(v) else v)

            # 如果提供了 batch_count 等旧参数也可以继续支持，但优先使用 cross_rules 行为
            return df

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
        
        # 如果需要分批建仓，则在buy信号处展开为多个子信号
        batch_count = int(self.parameters.get('batch_count', 1) or 1)
        batch_interval = int(self.parameters.get('batch_interval_bars', 1) or 1)
        batch_weights = self.parameters.get('batch_weights')

        # 解析 batch_weights：接受 list/tuple，或逗号分隔字符串，或 None
        if batch_weights is not None:
            if isinstance(batch_weights, str):
                try:
                    weights = [float(w.strip()) for w in batch_weights.split(',')]
                except Exception:
                    weights = None
            elif isinstance(batch_weights, (list, tuple)):
                try:
                    weights = [float(w) for w in batch_weights]
                except Exception:
                    weights = None
            else:
                weights = None
            # normalize if provided
            if weights is not None:
                total = sum(weights)
                if total <= 0:
                    weights = None
                else:
                    weights = [w / total for w in weights]
        else:
            weights = None

        # 默认均分
        if weights is None:
            weights = [1.0 / batch_count] * batch_count

        # 当 batch_count==1 则仅在原位保留 position_size
        if batch_count == 1:
            df.loc[df['signal'] == 1, 'position_size'] = weights[0]
            return df

        # 对于每个发生买入信号的索引，插入或标记后续 bars 作为子买单
        buy_indices = df.index[df['signal'] == 1].tolist()
        # 遍历并设置每个子批次
        for idx in buy_indices:
            for b in range(batch_count):
                target_idx = idx + b * batch_interval
                if target_idx >= len(df):
                    # 超出数据范围则跳过
                    continue
                # 如果原本在该位置已有卖出信号，则不覆盖卖出信号
                if df.at[target_idx, 'signal'] == -1:
                    # 冲突：在计划买入的位置出现卖出信号，跳过该子单
                    continue
                # 标记该位置为买入子单（可能覆盖原本的0）
                df.at[target_idx, 'signal'] = 1
                df.at[target_idx, 'trigger_reason'] = df.at[idx, 'trigger_reason'] + f" | batch_{b+1}/{batch_count}"
                df.at[target_idx, 'position_size'] = weights[b]

        return df 