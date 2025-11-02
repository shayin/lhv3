from src.backend.strategy.templates.strategy_template import StrategyTemplate
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class EnhancedMAStrategyV2(StrategyTemplate):
    """
    增强版移动平均线策略 V2 - 基于总资金的分批建仓和减仓
    
    与V1的主要区别：
    - V1: 分批加仓和减仓时，以当前持仓的xx%来当做一份份买卖
    - V2: 分批加仓和减仓时，以整个资金的xx%来当做一份份买卖
    
    建仓逻辑：
    - 当MA N1 上穿MA N2 时，执行总资金25%的仓位加仓（N1 < N2）
    - 当MA N2 上穿MA N3 时，再执行总资金25%的仓位加仓（N2 < N3）
    - 总建仓比例不超过100%，分阶段完成
    
    减仓逻辑：
    - 采用与建仓对称的反向信号执行减仓
    - 每次减仓比例为总资金的25%（而非当前持仓的25%）
    - 确保减仓信号触发条件与建仓逻辑完全对应
    """
    
    def __init__(self, name="增强版MA策略V2", data=None, parameters=None):
        """初始化策略"""
        default_params = {
            # MA周期参数 - 可配置，支持不同股票特性调优
            "n1": 5,    # 短期MA周期
            "n2": 10,   # 中期MA周期  
            "n3": 20,   # 长期MA周期
            
            # 分批建仓参数 - 基于总资金的百分比
            "position_per_stage": 0.25,  # 每阶段建仓比例（总资金的25%）
            "max_total_position": 1.0,   # 最大总仓位（总资金的100%）
            
            # 信号确认参数
            "signal_confirmation_bars": 1,  # 信号确认需要的K线数量
            "enable_position_tracking": True,  # 是否启用仓位跟踪
        }
        
        # 校验未知键与类型后再合并
        if parameters:
            unknown = set(parameters.keys()) - set(default_params.keys())
            if unknown:
                raise ValueError(f"存在未定义的参数: {sorted(list(unknown))}")
            for k, v in parameters.items():
                dv = default_params.get(k)
                if dv is None:
                    continue
                if isinstance(dv, float) and isinstance(v, (int, float)):
                    pass
                elif not isinstance(v, type(dv)):
                    raise ValueError(f"参数'{k}'类型不一致: 期望{type(dv).__name__}, 实际{type(v).__name__}")
            default_params.update(parameters)
            
        # 参数验证
        n1, n2, n3 = default_params["n1"], default_params["n2"], default_params["n3"]
        if not (n1 < n2 < n3):
            raise ValueError(f"MA周期参数必须满足 N1 < N2 < N3，当前: N1={n1}, N2={n2}, N3={n3}")
            
        super().__init__(name=name, data=data, parameters=default_params)
        
        # 仓位跟踪状态
        self.current_position = 0.0  # 当前总仓位（相对于总资金的比例）
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
            - position_size: 本次交易的仓位比例（相对于总资金）
            - stage: 交易阶段标识
        """
        if self.data is None or self.data.empty:
            logger.warning("未设置数据或数据为空，无法生成信号")
            return pd.DataFrame()
        
        # 获取参数
        n1 = self.parameters["n1"]
        n2 = self.parameters["n2"] 
        n3 = self.parameters["n3"]
        position_per_stage = self.parameters["position_per_stage"]
        
        logger.info(f"生成增强MA V2信号: N1={n1}, N2={n2}, N3={n3}, 每阶段仓位={position_per_stage}（基于总资金）")
        
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
        df['cumulative_position'] = 0.0  # 累计仓位跟踪（相对于总资金）
        
        # 仓位跟踪变量
        current_position = 0.0  # 当前总仓位（相对于总资金的比例）
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
                current_position < self.parameters["max_total_position"]):
                
                # 执行总资金25%建仓
                df.iloc[i, df.columns.get_loc('signal')] = 1
                df.iloc[i, df.columns.get_loc('position_size')] = position_per_stage
                df.iloc[i, df.columns.get_loc('stage')] = 'stage1_buy'
                df.iloc[i, df.columns.get_loc('trigger_reason')] = f"MA{n1}从下方上穿MA{n2}，执行第一阶段建仓{position_per_stage:.0%}（基于总资金）"
                
                current_position += position_per_stage
                stage1_active = True
                
                logger.info(f"[{current_date}] 阶段1建仓信号: MA{n1}上穿MA{n2}, 建仓{position_per_stage:.0%}（总资金）, 累计仓位: {current_position:.2%}")
            
            # 阶段2：N2上穿N3信号（需要在阶段1激活后）
            elif (current_row['ma_diff_23'] > 0 and prev_row['ma_diff_23'] <= 0 and 
                  stage1_active and current_position < self.parameters["max_total_position"]):
                
                # 执行总资金25%建仓
                df.iloc[i, df.columns.get_loc('signal')] = 1
                df.iloc[i, df.columns.get_loc('position_size')] = position_per_stage
                df.iloc[i, df.columns.get_loc('stage')] = 'stage2_buy'
                df.iloc[i, df.columns.get_loc('trigger_reason')] = f"MA{n2}从下方上穿MA{n3}，执行第二阶段建仓{position_per_stage:.0%}（基于总资金）"
                
                current_position += position_per_stage
                stage2_active = True
                
                logger.info(f"[{current_date}] 阶段2建仓信号: MA{n2}上穿MA{n3}, 建仓{position_per_stage:.0%}（总资金）, 累计仓位: {current_position:.2%}")
            
            # === 减仓信号检测（对称反向逻辑）===
            
            # 阶段2减仓：N2下穿N3信号（需要阶段2仓位存在）
            elif (current_row['ma_diff_23'] < 0 and prev_row['ma_diff_23'] >= 0 and 
                  stage2_active and current_position > 0):
                
                # 执行总资金25%减仓
                df.iloc[i, df.columns.get_loc('signal')] = -1
                df.iloc[i, df.columns.get_loc('position_size')] = position_per_stage
                df.iloc[i, df.columns.get_loc('stage')] = 'stage2_sell'
                df.iloc[i, df.columns.get_loc('trigger_reason')] = f"MA{n2}从上方下穿MA{n3}，执行第二阶段减仓{position_per_stage:.0%}（基于总资金）"
                
                current_position -= position_per_stage
                stage2_active = False
                
                logger.info(f"[{current_date}] 阶段2减仓信号: MA{n2}下穿MA{n3}, 减仓{position_per_stage:.0%}（总资金）, 累计仓位: {current_position:.2%}")
            
            # 阶段1减仓：N1下穿N2信号（需要阶段1仓位存在）
            elif (current_row['ma_diff_12'] < 0 and prev_row['ma_diff_12'] >= 0 and 
                  stage1_active and current_position > 0):
                
                # 执行总资金25%减仓
                df.iloc[i, df.columns.get_loc('signal')] = -1
                df.iloc[i, df.columns.get_loc('position_size')] = position_per_stage
                df.iloc[i, df.columns.get_loc('stage')] = 'stage1_sell'
                df.iloc[i, df.columns.get_loc('trigger_reason')] = f"MA{n1}从上方下穿MA{n2}，执行第一阶段减仓{position_per_stage:.0%}（基于总资金）"
                
                current_position -= position_per_stage
                
                # 如果仓位归零，重置所有阶段状态
                if current_position <= 0:
                    current_position = 0.0
                    stage1_active = False
                    stage2_active = False
                
                logger.info(f"[{current_date}] 阶段1减仓信号: MA{n1}下穿MA{n2}, 减仓{position_per_stage:.0%}（总资金）, 累计仓位: {current_position:.2%}")
            
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
        
        logger.info(f"V2信号生成完成 - 总买入: {buy_count}, 总卖出: {sell_count}")
        logger.info(f"阶段分布 - 阶段1建仓: {stage1_buy}, 阶段2建仓: {stage2_buy}, 阶段1减仓: {stage1_sell}, 阶段2减仓: {stage2_sell}")
        
        return df
    
    def suggest_position_size(self, signal: float, row: pd.Series = None) -> float:
        """
        建议仓位大小（基于总资金的比例）
        
        Args:
            signal: 交易信号值
            row: 当前行数据
            
        Returns:
            建议的仓位比例（相对于总资金）
        """
        if row is not None and 'position_size' in row and not pd.isna(row['position_size']):
            return float(row['position_size'])
        
        # 默认返回每阶段的标准仓位（基于总资金）
        return self.parameters["position_per_stage"]
    
    def reset_position_tracking(self):
        """重置仓位跟踪状态"""
        self.current_position = 0.0
        self.position_stages = {
            "stage1": False,
            "stage2": False,
        }
        logger.info("V2仓位跟踪状态已重置")
    
    def get_position_status(self) -> dict:
        """获取当前仓位状态"""
        return {
            "current_position": self.current_position,
            "stage1_active": self.position_stages["stage1"],
            "stage2_active": self.position_stages["stage2"],
            "max_position": self.parameters["max_total_position"],
            "version": "V2",
            "position_calculation": "基于总资金的百分比"
        }
    
    def get_strategy_info(self) -> dict:
        """获取策略信息"""
        return {
            "name": self.name,
            "version": "V2",
            "description": "增强版移动平均线策略V2 - 基于总资金的分批建仓和减仓",
            "key_features": [
                "基于总资金百分比的仓位管理",
                "分阶段建仓和减仓",
                "MA交叉信号确认",
                "智能仓位跟踪"
            ],
            "parameters": self.parameters,
            "difference_from_v1": "V2使用总资金的xx%进行分批交易，而V1使用当前持仓的xx%"
        }