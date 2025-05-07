import pandas as pd
import numpy as np
from datetime import datetime
import logging
import json
from multiprocessing import Pool, cpu_count
from typing import Dict, Any, List, Optional, Union

from ..config import DEFAULT_COMMISSION_RATE, DEFAULT_SLIPPAGE_RATE
from ..strategy.base import StrategyBase
from ..strategy.templates.strategy_template import StrategyTemplate

logger = logging.getLogger(__name__)

class BacktestEngine:
    """回测引擎，用于执行策略回测"""
    
    def __init__(self, data=None, strategy=None, initial_capital=100000.0, 
                 commission_rate=None, slippage_rate=None, start_date=None, end_date=None):
        """
        初始化回测引擎
        
        Args:
            data (pandas.DataFrame, optional): 市场数据
            strategy (StrategyBase, optional): 策略实例
            initial_capital (float, optional): 初始资金
            commission_rate (float, optional): 手续费率
            slippage_rate (float, optional): 滑点率
            start_date (str, optional): 回测开始日期，格式：YYYY-MM-DD
            end_date (str, optional): 回测结束日期，格式：YYYY-MM-DD
        """
        self.data = data
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate or DEFAULT_COMMISSION_RATE
        self.slippage_rate = slippage_rate or DEFAULT_SLIPPAGE_RATE
        self.start_date = start_date
        self.end_date = end_date
        
        # 回测结果
        self.results = {
            'trades': [],
            'performance': {},
            'equity_curve': None,
            'drawdowns': None,
            'signals': None
        }
        
        logger.info(f"回测引擎初始化完成: 初始资金={initial_capital}, 手续费率={commission_rate}, 滑点率={slippage_rate}")
        if start_date and end_date:
            logger.info(f"回测时间范围: {start_date} 至 {end_date}")
        
    def set_data(self, data):
        """设置回测数据"""
        self.data = data
        
    def set_strategy(self, strategy):
        """设置回测策略"""
        if not isinstance(strategy, StrategyBase):
            raise TypeError("策略必须继承自StrategyBase类")
            
        self.strategy = strategy
        
    def set_parameters(self, parameters):
        """设置回测参数"""
        if 'initial_capital' in parameters:
            self.initial_capital = parameters['initial_capital']
        if 'commission_rate' in parameters:
            self.commission_rate = parameters['commission_rate']
        if 'slippage_rate' in parameters:
            self.slippage_rate = parameters['slippage_rate']
        if 'start_date' in parameters:
            self.start_date = parameters['start_date']
        if 'end_date' in parameters:
            self.end_date = parameters['end_date']
            
    def run(self, data: Optional[pd.DataFrame] = None, benchmark_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            data: 可选，市场数据，如果为None则使用设置的数据
            benchmark_data: 可选，基准数据，用于计算alpha、beta等指标
            
        Returns:
            Dict[str, Any]: 回测结果
        """
        # 初始化结果记录
        self.results = {
            "equity_curve": [],
            "trades": [],
            "drawdowns": [],
            "performance": {}
        }
        
        # 使用参数中的数据或已设置的数据
        if data is not None:
            self.data = data.copy()
            logger.info(f"使用外部提供的回测数据，数据量: {len(data)}行")
        elif self.data is None or self.data.empty:
            raise ValueError("无法进行回测: 未提供市场数据")
        else:
            logger.info(f"使用策略数据进行回测，数据量: {len(self.data)}行")
        
        # 确保数据的日期列是datetime类型
        if 'date' in self.data.columns and self.data['date'].dtype != 'datetime64[ns]':
            self.data['date'] = pd.to_datetime(self.data['date'])
            logger.debug("将数据的date列转换为datetime类型")
        
        # 设置数据索引为日期，以便于后续处理
        if 'date' in self.data.columns and self.data.index.name != 'date':
            self.data = self.data.set_index('date')
            logger.debug("将数据的date列设置为索引")
        
        # 生成信号
        logger.info("开始生成交易信号...")
        signals = self.strategy.generate_signals()
        logger.info(f"信号生成完成，交易日总数: {len(signals)}")
        logger.debug(f"信号数据列: {signals.columns.tolist()}")

        # 打印部分信号数据用于调试
        if not signals.empty:
            sample_rows = min(5, len(signals))
            logger.debug(f"信号数据样本(前{sample_rows}行):\n{signals.head(sample_rows)}")

        # 添加统计信息以便调试
        buy_signals = (signals['signal'] == 1).sum() if 'signal' in signals.columns else 0
        sell_signals = (signals['signal'] == -1).sum() if 'signal' in signals.columns else 0
        logger.info(f"信号统计: 买入信号 {buy_signals}个, 卖出信号 {sell_signals}个")

        # 检查是否出现问题的信号
        if 'signal' in signals.columns:
            unique_signals = signals['signal'].unique()
            logger.debug(f"唯一的信号值: {unique_signals}")
            signal_counts = signals['signal'].value_counts().to_dict()
            logger.debug(f"信号值统计: {signal_counts}")
            
            # 检查是否有非数值类型的信号
            try:
                signals['signal'] = signals['signal'].astype(float)
                logger.debug("所有信号已转换为浮点数类型")
            except Exception as e:
                logger.error(f"信号类型转换失败: {e}")
                # 尝试识别非数值类型的行
                non_numeric = signals[pd.to_numeric(signals['signal'], errors='coerce').isna()]
                if not non_numeric.empty:
                    logger.error(f"存在非数值类型的信号，样本: \n{non_numeric.head()}")

        if 'signal' not in signals.columns:
            logger.error("生成的信号数据中没有'signal'列，无法执行交易")
            signals['signal'] = 0
        elif buy_signals == 0 and sell_signals == 0:
            logger.warning("生成的信号数据中没有买入或卖出信号，交易将为空")
            
            # 检查是否有非零信号
            if 'signal' in signals.columns:
                non_zero_signals = signals[signals['signal'] != 0]
                if not non_zero_signals.empty:
                    logger.debug(f"存在非零信号但不是1或-1，样本: \n{non_zero_signals.head()}")
                    # 尝试修正信号
                    logger.warning("尝试修正非标准信号值(将>0的设为1，<0的设为-1)")
                    signals.loc[signals['signal'] > 0, 'signal'] = 1
                    signals.loc[signals['signal'] < 0, 'signal'] = -1
                    # 重新统计修正后的信号
                    buy_signals = (signals['signal'] == 1).sum()
                    sell_signals = (signals['signal'] == -1).sum()
                    logger.info(f"信号修正后统计: 买入信号 {buy_signals}个, 卖出信号 {sell_signals}个")

        logger.info(f"信号内容: \n{signals}")
        
        # 确保信号数据的索引是datetime类型
        if not pd.api.types.is_datetime64_dtype(signals.index):
            try:
                signals.index = pd.to_datetime(signals.date)
                logger.debug("将信号数据的索引转换为datetime类型")
            except Exception as e:
                logger.error(f"转换信号索引为datetime失败: {e}")
                signals = signals.reset_index()
                if 'date' in signals.columns:
                    signals['date'] = pd.to_datetime(signals['date'])
                    signals = signals.set_index('date')
                    logger.debug("使用date列重设信号索引")

            logger.info(f"新信号内容: \n{signals}")
        # 处理日期范围 - 确保日期类型一致
        # if self.start_date:
        #     start_date = pd.to_datetime(self.start_date)
        #     signals = signals[signals.index >= start_date]
        #     logger.debug(f"按开始日期过滤: {start_date}")
        #     logger.debug(f"按开始日期过滤后: {signals}")
        
        # if self.end_date:
        #     end_date = pd.to_datetime(self.end_date)
        #     signals = signals[signals.index <= end_date]
        #     logger.debug(f"按结束日期过滤: {end_date}")
        #     logger.debug(f"按结束日期过滤后: {signals}")

        # logger.info(f"回测日期范围过滤后的交易日总数: {len(signals)}")
        
        # 执行交易
        logger.info("开始执行交易模拟...")
        self._simulate_trades(signals)
        
        # 计算性能指标
        logger.info("开始计算绩效指标...")
        self._calculate_performance(benchmark_data)
        
        # 返回回测结果
        result = {
            "equity_curve": self.results['equity_curve'],
            "trades": self.results['trades'],
            "drawdowns": self.results['drawdowns'],
            "total_return": self.results['performance'].get('total_return', 0.0),
            "annual_return": self.results['performance'].get('annual_return', 0.0),
            "sharpe_ratio": self.results['performance'].get('sharpe_ratio', 0.0),
            "max_drawdown": self.results['performance'].get('max_drawdown', 0.0),
            "win_rate": self.results['performance'].get('win_rate', 0.0),
            "profit_factor": self.results['performance'].get('profit_factor', 0.0),
            "alpha": self.results['performance'].get('alpha', 0.0),
            "beta": self.results['performance'].get('beta', 0.0)
        }
        
        # 检查结果中是否有非JSON兼容的值(inf, NaN)，并替换
        for key, value in result.items():
            if isinstance(value, float) and (np.isinf(value) or np.isnan(value)):
                if np.isinf(value) and value > 0:
                    result[key] = 999.99  # 替换正无穷
                elif np.isinf(value) and value < 0:
                    result[key] = -999.99  # 替换负无穷
                else:
                    result[key] = 0.0  # 替换NaN
        
        # 处理嵌套结构中的非JSON兼容值
        # 处理equity_curve
        if "equity_curve" in result and isinstance(result["equity_curve"], list):
            for i, item in enumerate(result["equity_curve"]):
                if isinstance(item, dict):
                    for k, v in item.items():
                        # 处理日期对象
                        if k == "date" and not isinstance(v, str):
                            result["equity_curve"][i][k] = str(v)
                        # 处理无穷大和NaN
                        elif isinstance(v, float) and (np.isinf(v) or np.isnan(v)):
                            if np.isinf(v) and v > 0:
                                result["equity_curve"][i][k] = 999.99
                            elif np.isinf(v) and v < 0:
                                result["equity_curve"][i][k] = -999.99
                            else:
                                result["equity_curve"][i][k] = 0.0
        
        # 处理drawdowns
        if "drawdowns" in result and isinstance(result["drawdowns"], list):
            for i, item in enumerate(result["drawdowns"]):
                if isinstance(item, dict):
                    for k, v in item.items():
                        # 处理日期对象
                        if k == "date" and not isinstance(v, str):
                            result["drawdowns"][i][k] = str(v)
                        # 处理无穷大和NaN
                        elif isinstance(v, float) and (np.isinf(v) or np.isnan(v)):
                            if np.isinf(v) and v > 0:
                                result["drawdowns"][i][k] = 999.99
                            elif np.isinf(v) and v < 0:
                                result["drawdowns"][i][k] = -999.99
                            else:
                                result["drawdowns"][i][k] = 0.0
        
        # 处理trades
        if "trades" in result and isinstance(result["trades"], list):
            for i, trade in enumerate(result["trades"]):
                if isinstance(trade, dict):
                    for k, v in trade.items():
                        # 处理日期对象
                        if k in ["date", "entry_date"] and not isinstance(v, str):
                            result["trades"][i][k] = str(v)
                        # 处理无穷大和NaN
                        elif isinstance(v, float) and (np.isinf(v) or np.isnan(v)):
                            if np.isinf(v) and v > 0:
                                result["trades"][i][k] = 999.99
                            elif np.isinf(v) and v < 0:
                                result["trades"][i][k] = -999.99
                            else:
                                result["trades"][i][k] = 0.0
        
        logger.info(f"回测完成: 总收益率={result['total_return']:.2%}, 最大回撤={result['max_drawdown']:.2%}, 夏普比率={result['sharpe_ratio']:.2f}")
        logger.info(f"交易统计: 总交易次数={len(self.results['trades'])}, 胜率={result['win_rate']:.2%}")
        
        return result
    
    def run_parallel(self, parameter_sets):
        """
        并行运行多组参数的回测
        
        Args:
            parameter_sets (list): 参数集列表，每个元素是一个字典
            
        Returns:
            list: 回测结果列表
        """
        if self.data is None or self.data.empty:
            raise ValueError("无法进行回测: 未提供市场数据")
            
        if self.strategy is None:
            raise ValueError("无法进行回测: 未提供交易策略")
            
        # 过滤数据
        filtered_data = self._filter_data()
        
        # 准备并行计算
        num_cores = min(cpu_count(), len(parameter_sets))
        pool = Pool(processes=num_cores)
        
        # 创建任务
        tasks = []
        for params in parameter_sets:
            task_params = {
                "data": filtered_data,
                "strategy_class": self.strategy.__class__,
                "parameters": params,
                "initial_capital": self.initial_capital,
                "commission_rate": self.commission_rate,
                "slippage_rate": self.slippage_rate
            }
            tasks.append(task_params)
        
        # 并行执行回测
        results = pool.map(self._run_single_backtest_wrapper, tasks)
        
        # 关闭进程池
        pool.close()
        pool.join()
        
        return results
    
    @staticmethod
    def _run_single_backtest_wrapper(params):
        """包装单次回测函数，用于并行计算"""
        engine = BacktestEngine()
        return engine._run_single_backtest(params)
    
    def _run_single_backtest(self, params):
        """
        运行单次回测，用于并行计算
        
        Args:
            params (dict): 参数字典，包含data, strategy_class, parameters等
            
        Returns:
            dict: 回测结果
        """
        data = params["data"]
        strategy_class = params["strategy_class"]
        parameters = params["parameters"]
        initial_capital = params["initial_capital"]
        commission_rate = params["commission_rate"]
        slippage_rate = params["slippage_rate"]
        
        # 创建策略实例
        strategy = strategy_class(parameters=parameters)
        
        # 设置数据和参数
        strategy.set_data(data)
        
        strategy_params = strategy.parameters.copy()
        strategy_params['commission_rate'] = commission_rate
        strategy_params['slippage_rate'] = slippage_rate
        strategy.set_parameters(strategy_params)
        
        # 初始化策略
        strategy.initialize(initial_capital)
        
        # 执行回测
        backtest_results = strategy.backtest()
        
        # 添加参数信息
        backtest_results['parameters'] = parameters
        
        return backtest_results
    
    def _filter_data(self):
        """
        按照回测时间范围过滤数据
        
        Returns:
            pandas.DataFrame: 过滤后的数据
        """
        filtered_data = self.data.copy()
        
        # 确保日期列是datetime类型
        if 'date' in filtered_data.columns:
            if filtered_data['date'].dtype != 'datetime64[ns]':
                filtered_data['date'] = pd.to_datetime(filtered_data['date'])
        
        # 按照开始日期过滤
        if self.start_date:
            start_date = pd.to_datetime(self.start_date)
            filtered_data = filtered_data[filtered_data['date'] >= start_date]
            
        # 按照结束日期过滤
        if self.end_date:
            end_date = pd.to_datetime(self.end_date)
            filtered_data = filtered_data[filtered_data['date'] <= end_date]
            
        return filtered_data
    
    def save_results(self, filename):
        """
        保存回测结果到文件
        
        Args:
            filename (str): 文件名
            
        Returns:
            str: 文件路径
        """
        # 将回测结果转换为JSON
        results_json = {
            'strategy_name': self.strategy.name if self.strategy else '',
            'parameters': self.strategy.parameters if self.strategy else {},
            'initial_capital': self.initial_capital,
            'commission_rate': self.commission_rate,
            'slippage_rate': self.slippage_rate,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'performance': self.results['performance'],
            'trades': [self._convert_trade_to_dict(trade) for trade in self.results['trades']]
        }
        
        # 添加权益曲线和回撤
        if self.results['equity_curve']:
            results_json['equity_curve'] = self.results['equity_curve']
        
        if self.results['drawdowns']:
            results_json['drawdowns'] = self.results['drawdowns']
        
        # 保存到文件
        with open(filename, 'w') as f:
            json.dump(results_json, f, indent=4, default=str)
            
        logger.info(f"回测结果已保存至: {filename}")
        
        return filename
    
    def _convert_trade_to_dict(self, trade):
        """将交易记录转换为字典"""
        if isinstance(trade, dict):
            # 处理日期和时间
            result = trade.copy()
            if 'date' in result and not isinstance(result['date'], str):
                result['date'] = str(result['date'])
            return result
        else:
            # 如果已经是字典，直接返回
            return trade 

    def _simulate_trades(self, signals: pd.DataFrame) -> None:
        """
        模拟交易过程
        
        Args:
            signals: 包含交易信号的DataFrame
        """
        logger.debug("开始模拟交易过程...")
        
        # 检查信号数据
        if 'signal' not in signals.columns:
            logger.error("信号数据中没有'signal'列，无法执行交易")
            return
        
        # 检查是否有买入或卖出信号
        buy_signals = (signals['signal'] == 1).sum()
        sell_signals = (signals['signal'] == -1).sum()
        logger.debug(f"交易信号统计: 买入信号 {buy_signals}个, 卖出信号 {sell_signals}个")
        
        if buy_signals == 0:
            logger.warning("没有买入信号，可能导致无交易")
        
        # 初始化权益曲线
        self.results['equity_curve'] = []
        self.results['trades'] = []
        self.capital = self.initial_capital
        self.equity = self.initial_capital
        self.position = 0
        self.position_value = 0.0
        self.position_avg_price = 0.0
        
        # 回测过程中的指标
        max_equity = self.equity  # 历史最高总资产
        current_drawdown = 0.0  # 当前回撤
        
        # 添加起始点到权益曲线
        if not signals.empty:
            first_date = signals.index[0]
            # 取出第一个交易日的收盘价作为默认值
            first_close = float(signals.iloc[0].get("close", 0))
            self.results['equity_curve'].append({
                "date": first_date,
                "equity": self.equity,
                "capital": self.capital,
                "position": self.position,
                "position_value": self.position_value,
                "drawdown": current_drawdown,
                # 添加当日K线价格数据
                "open": signals.iloc[0].get("open", first_close) if signals.iloc[0].get("open") and float(signals.iloc[0].get("open", 0)) > 0 else first_close,
                "high": signals.iloc[0].get("high", first_close) if signals.iloc[0].get("high") and float(signals.iloc[0].get("high", 0)) > 0 else first_close,
                "low": signals.iloc[0].get("low", first_close) if signals.iloc[0].get("low") and float(signals.iloc[0].get("low", 0)) > 0 else first_close,
                "close": first_close,
                "volume": signals.iloc[0].get("volume", 0)
            })
        
        previous_trade_date = None  # 上一次交易日，用于计算持仓天数
        entry_price = None  # 买入价格
        entry_date = None  # 买入日期
        
        # 遍历每个交易日
        for date, row in signals.iterrows():
            price = float(row["close"])
            # 确保signal是数值类型
            try:
                signal = float(row["signal"]) if "signal" in row else 0
            except (TypeError, ValueError):
                logger.warning(f"日期 {date} 的信号类型错误，设为默认值0")
                signal = 0
            
            trigger_reason = row.get("trigger_reason", "未记录")
            
            # 记录交易前状态
            before_capital = self.capital
            before_equity = self.equity
            
            if signal != 0:
                logger.debug(f"日期: {date}, 价格: {price}, 信号: {signal}, 当前持仓: {self.position}")
            
            # 根据信号执行交易
            if signal == 1 and self.position == 0:  # 买入信号且当前无持仓
                logger.info(f"检测到买入信号: 日期={date}, 价格={price}, 信号值={signal}, 触发原因={trigger_reason}")
                
                # 计算可买数量
                # 考虑手续费后的最大可买股数
                # 计算方法: 资金 / (价格 * (1 + 滑点率) * (1 + 手续费率))
                execution_price = price * (1 + self.slippage_rate)  # 考虑滑点
                # 这里修正手续费率计算，将decimal值(0.15)转为百分比(0.0015)
                actual_commission_rate = self.commission_rate / 100 if self.commission_rate > 0.01 else self.commission_rate
                max_shares = int(self.capital / (execution_price * (1 + actual_commission_rate)))  # 确保股数为整数
                shares = max_shares  # 这里可以根据策略调整买入数量
                
                # 执行买入
                cost = shares * execution_price
                commission_fee = cost * actual_commission_rate
                total_cost = cost + commission_fee
                
                logger.debug(f"买入计算: 最大可买={max_shares}股, 执行价格={execution_price}, 成本={cost}, 手续费率={actual_commission_rate:.6f}, 手续费={commission_fee}, 总成本={total_cost}, 当前资金={self.capital}")
                
                if total_cost <= self.capital and shares > 0:
                    self.capital -= total_cost
                    self.position = shares
                    self.position_avg_price = execution_price
                    self.position_value = shares * price
                    
                    # 记录买入交易
                    entry_price = execution_price
                    entry_date = date
                    
                    trade = {
                        "date": date,
                        "action": "BUY",
                        "price": execution_price,
                        "shares": shares,
                        "value": cost,
                        "commission": commission_fee,
                        "before_cash": before_capital,
                        "after_cash": self.capital,
                        "before_equity": before_equity,
                        "after_equity": self.capital + self.position_value,
                        "trigger_reason": trigger_reason
                    }
                    self.results['trades'].append(trade)
                    
                    logger.info(f"买入: 日期={date}, 价格={execution_price:.4f}, 数量={shares}, 金额={cost:.2f}, 手续费={commission_fee:.2f}")
                else:
                    logger.warning(f"买入失败: 资金不足或股数为0, 当前资金={self.capital}, 需要资金={total_cost}, 股数={shares}")
            
            elif signal == -1 and self.position > 0:  # 卖出信号且当前有持仓
                logger.info(f"检测到卖出信号: 日期={date}, 价格={price}, 信号值={signal}, 触发原因={trigger_reason}")
                
                # 执行卖出
                execution_price = price * (1 - self.slippage_rate)  # 考虑滑点
                shares = self.position
                revenue = shares * execution_price
                # 修正手续费率计算
                actual_commission_rate = self.commission_rate / 100 if self.commission_rate > 0.01 else self.commission_rate
                commission_fee = revenue * actual_commission_rate
                net_revenue = revenue - commission_fee
                
                # 计算收益
                profit = net_revenue - (shares * self.position_avg_price)
                profit_percent = profit / (shares * self.position_avg_price) if self.position_avg_price > 0 else 0
                
                # 计算持仓天数
                if previous_trade_date and entry_date:
                    holding_days = (datetime.strptime(str(date)[:10], "%Y-%m-%d") - 
                                    datetime.strptime(str(entry_date)[:10], "%Y-%m-%d")).days
                else:
                    holding_days = 0
                
                self.capital += net_revenue
                self.position = 0
                self.position_value = 0
                self.position_avg_price = 0
                
                # 记录卖出交易
                trade = {
                    "date": date,
                    "action": "SELL",
                    "price": execution_price,
                    "shares": shares,
                    "value": revenue,
                    "commission": commission_fee,
                    "profit": profit,
                    "profit_percent": profit_percent,
                    "entry_price": entry_price,
                    "entry_date": entry_date,
                    "holding_days": holding_days,
                    "before_cash": before_capital,
                    "after_cash": self.capital,
                    "before_equity": before_equity,
                    "after_equity": self.capital,
                    "trigger_reason": trigger_reason
                }
                self.results['trades'].append(trade)
                
                # 重置入场信息
                entry_price = None
                entry_date = None
                
                logger.info(f"卖出: 日期={date}, 价格={execution_price:.4f}, 数量={shares}, 金额={revenue:.2f}, 手续费={commission_fee:.2f}, 收益={profit:.2f}({profit_percent:.2%})")
            
            # 更新持仓市值
            if self.position > 0:
                self.position_value = self.position * price
            
            # 更新总资产
            self.equity = self.capital + self.position_value
            
            # 计算回撤
            if self.equity > max_equity:
                max_equity = self.equity
                current_drawdown = 0.0
            else:
                current_drawdown = (max_equity - self.equity) / max_equity
            
            # 添加当日数据到权益曲线
            self.results['equity_curve'].append({
                "date": date,
                "equity": self.equity,
                "capital": self.capital,
                "position": self.position,
                "position_value": self.position_value,
                "drawdown": current_drawdown,
                # 添加当日K线价格数据
                "open": row.get("open", price) if row.get("open") and float(row.get("open", 0)) > 0 else price,
                "high": row.get("high", price) if row.get("high") and float(row.get("high", 0)) > 0 else price,
                "low": row.get("low", price) if row.get("low") and float(row.get("low", 0)) > 0 else price,
                "close": price,  # 这里保持不变，因为price就是收盘价
                "volume": row.get("volume", 0)
            })
            
            # 添加回撤记录
            self.results['drawdowns'].append({
                "date": date,
                "drawdown": current_drawdown
            })
            
            previous_trade_date = date
        
        logger.debug(f"交易模拟完成: 总交易次数={len(self.results['trades'])}, 最终资产={self.equity:.2f}")
    
    def _calculate_performance(self, benchmark_data: Optional[pd.DataFrame] = None) -> None:
        """
        计算回测性能指标
        
        Args:
            benchmark_data: 基准数据，用于计算alpha、beta等指标
        """
        if not self.results['equity_curve']:
            logger.warning("权益曲线为空，无法计算性能指标")
            return
        
        # 计算总收益率
        final_equity = self.results['equity_curve'][-1]["equity"]
        self.results['performance']['total_return'] = (final_equity / self.initial_capital) - 1
        
        # 计算年化收益率
        if len(self.results['equity_curve']) > 1:
            start_date = self.results['equity_curve'][0]["date"]
            end_date = self.results['equity_curve'][-1]["date"]
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
            
            days = (end_date - start_date).days
            if days > 0:
                self.results['performance']['annual_return'] = pow((1 + self.results['performance']['total_return']), (365 / days)) - 1
        
        # 计算最大回撤
        if self.results['drawdowns']:
            self.results['performance']['max_drawdown'] = max([d["drawdown"] for d in self.results['drawdowns']])
        
        # 计算胜率
        win_trades = [t for t in self.results['trades'] if t["action"] == "SELL" and t.get("profit", 0) > 0]
        lose_trades = [t for t in self.results['trades'] if t["action"] == "SELL" and t.get("profit", 0) <= 0]
        total_sell_trades = len(win_trades) + len(lose_trades)
        
        if total_sell_trades > 0:
            self.results['performance']['win_rate'] = len(win_trades) / total_sell_trades
        
        # 计算盈亏比
        total_profit = sum([t.get("profit", 0) for t in win_trades])
        total_loss = abs(sum([t.get("profit", 0) for t in lose_trades]))
        
        if total_loss > 0:
            self.results['performance']['profit_factor'] = total_profit / total_loss
        else:
            # 如果没有亏损交易，设置盈亏比为一个大的有限数值
            if total_profit > 0:
                self.results['performance']['profit_factor'] = 999.99  # 使用一个有限的大数值代替无穷大
            else:
                self.results['performance']['profit_factor'] = 0.0  # 如果既没有盈利也没有亏损
        
        # 计算夏普比率
        if len(self.results['equity_curve']) > 1:
            # 提取权益数据计算收益率序列
            equity_values = [ec["equity"] for ec in self.results['equity_curve']]
            returns = pd.Series(equity_values).pct_change().dropna()
            
            # 计算年化收益率和年化标准差
            annual_std = returns.std() * np.sqrt(252)
            risk_free_rate = 0.02  # 假设无风险利率2%
            
            # 计算夏普比率
            if annual_std > 0:
                self.results['performance']['sharpe_ratio'] = (self.results['performance']['annual_return'] - risk_free_rate) / annual_std
        
        # 计算Alpha和Beta(需要基准数据)
        if benchmark_data is not None and not benchmark_data.empty:
            # 待实现
            pass
        
        logger.info(f"性能指标计算完成: 总收益率={self.results['performance']['total_return']:.2%}, 年化收益率={self.results['performance']['annual_return']:.2%}, 最大回撤={self.results['performance']['max_drawdown']:.2%}")
        if total_sell_trades > 0:
            logger.info(f"交易统计: 总交易次数={total_sell_trades}, 盈利交易={len(win_trades)}, 亏损交易={len(lose_trades)}, 胜率={self.results['performance']['win_rate']:.2%}, 盈亏比={self.results['performance']['profit_factor']:.2f}") 