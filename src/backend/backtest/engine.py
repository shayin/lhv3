import pandas as pd
import numpy as np
from datetime import datetime
import logging
import json
from multiprocessing import Pool, cpu_count

from ..config import DEFAULT_COMMISSION_RATE, DEFAULT_SLIPPAGE_RATE
from ..strategy.base import StrategyBase

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
            
    def run(self):
        """
        运行回测
        
        Returns:
            dict: 回测结果
        """
        if self.data is None or self.data.empty:
            raise ValueError("无法进行回测: 未提供市场数据")
            
        if self.strategy is None:
            raise ValueError("无法进行回测: 未提供交易策略")
            
        # 过滤数据
        filtered_data = self._filter_data()
        
        # 准备策略
        self.strategy.set_data(filtered_data)
        
        # 设置策略参数
        strategy_params = self.strategy.parameters.copy()
        strategy_params['commission_rate'] = self.commission_rate
        strategy_params['slippage_rate'] = self.slippage_rate
        self.strategy.set_parameters(strategy_params)
        
        # 初始化策略
        self.strategy.initialize(self.initial_capital)
        
        # 执行回测
        backtest_results = self.strategy.backtest()
        
        # 保存回测结果
        self.results['trades'] = backtest_results.get('trades', [])
        self.results['performance'] = backtest_results.get('performance', {})
        self.results['equity_curve'] = backtest_results.get('equity_curve', None)
        self.results['drawdowns'] = backtest_results.get('drawdowns', None)
        self.results['signals'] = backtest_results.get('signals', None)
        
        return self.results
    
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