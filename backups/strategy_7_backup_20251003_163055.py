from src.backend.strategy.base.strategy_base import StrategyBase
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class EnhancedMAStrategy(StrategyBase):
    """
    增强版移动平均线策略 - 支持智能分批建仓和减仓
    
    建仓逻辑：
    - 当MA N1 上穿MA N2 时，执行25%仓位加仓（N1 < N2）
    - 当MA N2 上穿MA N3 时，再执行25%仓位加仓（N2 < N3）
    - 总建仓比例不超过100%，分阶段完成
    
    减仓逻辑：
    - 采用与建仓对称的反向信号执行减仓
    - 每次减仓比例严格匹配建仓比例（25%）
    - 确保减仓信号触发条件与建仓逻辑完全对应
    """
    
    def __init__(self, parameters=None):
        """初始化策略"""
        default_params = {
            # MA周期参数 - 可配置，支持不同股票特性调优
            "n1": 5,    # 短期MA周期
            "n2": 10,   # 中期MA周期  
            "n3": 20,   # 长期MA周期
            
            # 分批建仓参数
            "position_per_stage": 0.25,  # 每阶段建仓比例（25%）
            "max_total_position": 1.0,   # 最大总仓位（100%）
            
            # 信号确认参数
            "signal_confirmation_bars": 1,  # 信号确认需要的K线数量
            "enable_position_tracking": True,  # 是否启用仓位跟踪
        }
        
        # 合并用户参数与默认参数
        if parameters:
            default_params.update(parameters)
            
        # 参数验证
        n1, n2, n3 = default_params["n1"], default_params["n2"], default_params["n3"]
        if not (n1 < n2 < n3):
            raise ValueError(f"MA周期参数必须满足 N1 < N2 < N3，当前: N1={n1}, N2={n2}, N3={n3}")
            
        super().__init__(params=default_params, name="增强版MA策略")
        
        # 仓位跟踪状态
        self.current_position = 0.0  # 当前总仓位
        self.position_stages = {     # 各阶段仓位状态
            "stage1": False,  # N1上穿N2阶段
            "stage2": False,  # N2上穿N3阶段
        }
    
    def generate_signals(self) -> pd.DataFrame:
        """
        生成交易信号
        
        Returns:
            包含信号的DataFrame，包括:
            - signal: 交易信号 (1: 买入, -1: 卖出, 0: 不操作)
            - trigger_reason: 信号触发原因
            - position_size: 本次交易的仓位比例
            - stage: 交易阶段标识
        """
        if self.data is None or self.data.empty:
            logger.warning("未设置数据或数据为空，无法生成信号")
            return pd.DataFrame()
        
        # 获取参数
        n1 = self.params["n1"]
        n2 = self.params["n2"] 
        n3 = self.params["n3"]
        position_per_stage = self.params["position_per_stage"]
        
        logger.info(f"生成增强MA信号: N1={n1}, N2={n2}, N3={n3}, 每阶段仓位={position_per_stage}")
        
        # 计算指标
        df = self.data.copy()
        
        # 计算三条移动平均线
        df[f'ma_{n1}'] = df['close'].rolling(window=n1).mean()
        df[f'ma_{n2}'] = df['close'].rolling(window=n2).mean()
        df[f'ma_{n3}'] = df['close'].rolling(window=n3).mean()
        
        # 计算MA差值和前一日差值（用于判断穿越）
        df['ma_diff_12'] = df[f'ma_{n1}'] - df[f'ma_{n2}']  # N1与N2的差值
        df['ma_diff_23'] = df[f'ma_{n2}'] - df[f'ma_{n3}']  # N2与N3的差值
        df['prev_ma_diff_12'] = df['ma_diff_12'].shift(1)
        df['prev_ma_diff_23'] = df['ma_diff_23'].shift(1)
        
        # 初始化信号列
        df['signal'] = 0
        df['trigger_reason'] = ''
        df['position_size'] = np.nan
        df['stage'] = ''
        df['cumulative_position'] = 0.0  # 累计仓位跟踪
        
        # 仓位跟踪变量
        current_position = 0.0
        stage1_active = False  # N1上穿N2阶段是否激活
        stage2_active = False  # N2上穿N3阶段是否激活
        
        # 逐行处理信号生成
        for i in range(1, len(df)):  # 从第二行开始，因为需要前一日数据
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # 当前日期（用于日志）
            current_date = df.index[i] if hasattr(df.index[i], 'strftime') else str(df.index[i])
            
            # === 建仓信号检测 ===
            
            # 阶段1：N1上穿N2信号
            if (current_row['ma_diff_12'] > 0 and prev_row['ma_diff_12'] <= 0 and 
                current_position < self.params["max_total_position"]):
                
                # 执行25%建仓
                df.iloc[i, df.columns.get_loc('signal')] = 1
                df.iloc[i, df.columns.get_loc('position_size')] = position_per_stage
                df.iloc[i, df.columns.get_loc('stage')] = 'stage1_buy'
                df.iloc[i, df.columns.get_loc('trigger_reason')] = f"MA{n1}从下方上穿MA{n2}，执行第一阶段建仓25%"
                
                current_position += position_per_stage
                stage1_active = True
                
                logger.info(f"[{current_date}] 阶段1建仓信号: MA{n1}上穿MA{n2}, 建仓25%, 累计仓位: {current_position:.2%}")
            
            # 阶段2：N2上穿N3信号（需要在阶段1激活后）
            elif (current_row['ma_diff_23'] > 0 and prev_row['ma_diff_23'] <= 0 and 
                  stage1_active and current_position < self.params["max_total_position"]):
                
                # 执行25%建仓
                df.iloc[i, df.columns.get_loc('signal')] = 1
                df.iloc[i, df.columns.get_loc('position_size')] = position_per_stage
                df.iloc[i, df.columns.get_loc('stage')] = 'stage2_buy'
                df.iloc[i, df.columns.get_loc('trigger_reason')] = f"MA{n2}从下方上穿MA{n3}，执行第二阶段建仓25%"
                
                current_position += position_per_stage
                stage2_active = True
                
                logger.info(f"[{current_date}] 阶段2建仓信号: MA{n2}上穿MA{n3}, 建仓25%, 累计仓位: {current_position:.2%}")
            
            # === 减仓信号检测（对称反向逻辑）===
            
            # 阶段2减仓：N2下穿N3信号（需要阶段2仓位存在）
            elif (current_row['ma_diff_23'] < 0 and prev_row['ma_diff_23'] >= 0 and 
                  stage2_active and current_position > 0):
                
                # 执行25%减仓
                df.iloc[i, df.columns.get_loc('signal')] = -1
                df.iloc[i, df.columns.get_loc('position_size')] = position_per_stage
                df.iloc[i, df.columns.get_loc('stage')] = 'stage2_sell'
                df.iloc[i, df.columns.get_loc('trigger_reason')] = f"MA{n2}从上方下穿MA{n3}，执行第二阶段减仓25%"
                
                current_position -= position_per_stage
                stage2_active = False
                
                logger.info(f"[{current_date}] 阶段2减仓信号: MA{n2}下穿MA{n3}, 减仓25%, 累计仓位: {current_position:.2%}")
            
            # 阶段1减仓：N1下穿N2信号（需要阶段1仓位存在）
            elif (current_row['ma_diff_12'] < 0 and prev_row['ma_diff_12'] >= 0 and 
                  stage1_active and current_position > 0):
                
                # 执行25%减仓
                df.iloc[i, df.columns.get_loc('signal')] = -1
                df.iloc[i, df.columns.get_loc('position_size')] = position_per_stage
                df.iloc[i, df.columns.get_loc('stage')] = 'stage1_sell'
                df.iloc[i, df.columns.get_loc('trigger_reason')] = f"MA{n1}从上方下穿MA{n2}，执行第一阶段减仓25%"
                
                current_position -= position_per_stage
                
                # 如果仓位归零，重置所有阶段状态
                if current_position <= 0:
                    current_position = 0.0
                    stage1_active = False
                    stage2_active = False
                
                logger.info(f"[{current_date}] 阶段1减仓信号: MA{n1}下穿MA{n2}, 减仓25%, 累计仓位: {current_position:.2%}")
            
            # 更新累计仓位跟踪
            df.iloc[i, df.columns.get_loc('cumulative_position')] = current_position
        
        # 确保仓位比例在合理范围内
        df['position_size'] = df['position_size'].apply(
            lambda x: max(0.0, min(x, 1.0)) if not pd.isna(x) else x
        )
        
        # 统计信号数量
        buy_count = (df['signal'] == 1).sum()
        sell_count = (df['signal'] == -1).sum()
        stage1_buy = (df['stage'] == 'stage1_buy').sum()
        stage2_buy = (df['stage'] == 'stage2_buy').sum()
        stage1_sell = (df['stage'] == 'stage1_sell').sum()
        stage2_sell = (df['stage'] == 'stage2_sell').sum()
        
        logger.info(f"信号生成完成 - 总买入: {buy_count}, 总卖出: {sell_count}")
        logger.info(f"阶段分布 - 阶段1建仓: {stage1_buy}, 阶段2建仓: {stage2_buy}, 阶段1减仓: {stage1_sell}, 阶段2减仓: {stage2_sell}")
        
        return df
    
    def suggest_position_size(self, signal: float, row: pd.Series = None) -> float:
        """
        建议仓位大小
        
        Args:
            signal: 交易信号值
            row: 当前行数据
            
        Returns:
            建议的仓位比例
        """
        if row is not None and 'position_size' in row and not pd.isna(row['position_size']):
            return float(row['position_size'])
        
        # 默认返回每阶段的标准仓位
        return self.parameters["position_per_stage"]
    
    def reset_position_tracking(self):
        """重置仓位跟踪状态"""
        self.current_position = 0.0
        self.position_stages = {
            "stage1": False,
            "stage2": False,
        }
        logger.info("仓位跟踪状态已重置")
    
    def get_position_status(self) -> dict:
        """获取当前仓位状态"""
        return {
            "current_position": self.current_position,
            "stage1_active": self.position_stages["stage1"],
            "stage2_active": self.position_stages["stage2"],
            "max_position": self.parameters["max_total_position"]
        }