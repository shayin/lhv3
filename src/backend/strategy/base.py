import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class StrategyBase(ABC):
    """策略基类，所有策略都应该继承此类"""
    
    def __init__(self, name=None, parameters=None):
        """
        初始化策略
        
        Args:
            name (str): 策略名称
            parameters (dict, optional): 策略参数
        """
        self.name = name or "未命名策略"
        self.parameters = parameters or {}
        self.data = None
        self.positions = {}  # 持仓信息，格式: {symbol: quantity}
        self.cash = 0      # 当前现金
        self.initial_cash = 0  # 初始资金
        self.trades = []   # 交易记录
        
    def set_data(self, data):
        """
        设置策略使用的数据
        
        Args:
            data (pandas.DataFrame): 市场数据
        """
        self.data = data
        
    def set_parameters(self, parameters):
        """
        设置策略参数
        
        Args:
            parameters (dict): 策略参数
        """
        self.parameters.update(parameters)
        
    def initialize(self, cash=100000.0):
        """
        初始化策略的资金和持仓
        
        Args:
            cash (float): 初始资金
        """
        self.cash = cash
        self.initial_cash = cash
        self.positions = {}
        self.trades = []
        
    @abstractmethod
    def generate_signals(self):
        """
        生成交易信号
        
        Returns:
            pandas.DataFrame: 包含交易信号的DataFrame
        """
        pass
    
    def execute_trades(self, signals):
        """
        严格按照策略信号执行交易
        
        Args:
            signals (pandas.DataFrame): 包含交易信号的DataFrame
            
        Returns:
            list: 交易记录列表
        """
        if signals is None or signals.empty:
            return []
            
        trades = []
        current_position = 0  # 跟踪当前持仓状态
        last_signal = 0  # 上一个信号
        
        # 获取默认的股票代码
        default_symbol = self.data['symbol'].iloc[0] if 'symbol' in self.data.columns else 'default'
        
        # 获取仓位配置
        position_config = self.parameters.get('positionConfig', {})
        position_mode = position_config.get('mode', 'fixed')  # 默认为固定比例模式
        default_position_size = position_config.get('defaultSize', 1.0)  # 默认100%仓位
        position_sizes = position_config.get('sizes', [0.25, 0.25, 0.25, 0.25])  # 默认分批建仓比例
        dynamic_max = position_config.get('dynamicMax', 1.0)  # 动态模式的最大仓位
        
        # 分批建仓的当前批次
        current_stage = 0
        available_capital = self.cash  # 可用资金
        allocated_capital = 0  # 已分配资金
        
        # 遍历所有数据点，严格按照信号执行交易
        for i, row in signals.iterrows():
            date = row['date']
            symbol = row.get('symbol', default_symbol)
            price = row['close']
            signal = row.get('signal', 0)
            
            # 转换日期格式
            if isinstance(date, str):
                date = pd.to_datetime(date)
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            
            # 信号变化为买入点
            if signal > 0 and last_signal <= 0 and current_position < 1:  # 允许部分仓位，所以检查 < 1而不是 == 0
                # 根据不同的仓位模式计算买入仓位
                position_size = 1.0  # 默认全仓
                
                if position_mode == 'fixed':
                    # 固定比例模式
                    position_size = default_position_size
                elif position_mode == 'dynamic':
                    # 动态比例模式，根据信号强度决定仓位
                    signal_strength = min(abs(signal), 1.0)  # 确保信号强度在0-1之间
                    position_size = signal_strength * dynamic_max
                elif position_mode == 'staged' and current_stage < len(position_sizes):
                    # 分批建仓模式
                    position_size = position_sizes[current_stage]
                    current_stage += 1
                
                # 确保仓位在0-1之间
                position_size = max(0.01, min(position_size, 1.0))
                
                # 计算本次交易可用资金
                trade_cash = available_capital * position_size
                
                # 计算可以买入的最大数量
                commission_rate = self.parameters.get('commission_rate', 0.0003)
                denominator = price * (1 + commission_rate)
                max_quantity = int(trade_cash / denominator) if denominator > 0 else 0
                
                if max_quantity > 0:
                    # 计算交易成本
                    cost = max_quantity * price
                    commission = cost * commission_rate
                    total_cost = cost + commission
                    
                    # 更新资金和持仓
                    available_capital -= total_cost
                    allocated_capital += total_cost
                    self.cash -= total_cost
                    self.positions[symbol] = self.positions.get(symbol, 0) + max_quantity
                    current_position += position_size  # 更新当前仓位状态
                    
                    # 记录交易
                    trade = {
                        'date': date_str,
                        'symbol': symbol,
                        'action': 'BUY',
                        'price': float(price),
                        'quantity': max_quantity,
                        'commission': float(commission),
                        'cost': float(total_cost),
                        'signal': float(signal),
                        'position_size': float(position_size),  # 记录本次交易的仓位比例
                        'available_capital': float(available_capital),  # 记录交易后的可用资金
                        'allocated_capital': float(allocated_capital)  # 记录已分配资金
                    }
                    trades.append(trade)
                    self.trades.append(trade)
            
            # 信号变化为卖出点
            elif signal < 0 and last_signal >= 0 and current_position > 0:
                # 获取当前持仓
                quantity = self.positions.get(symbol, 0)
                
                if quantity > 0:
                    # 计算交易收益
                    commission_rate = self.parameters.get('commission_rate', 0.0003)
                    revenue = quantity * price
                    commission = revenue * commission_rate
                    total_revenue = revenue - commission
                    
                    # 更新资金和持仓
                    available_capital += total_revenue
                    allocated_capital = 0  # 清空已分配资金
                    self.cash += total_revenue
                    self.positions[symbol] = 0
                    current_position = 0  # 清空仓位
                    current_stage = 0  # 重置分批建仓阶段
                    
                    # 查找对应的买入交易以计算盈亏
                    entry_price = None
                    for t in reversed(self.trades):
                        if t['action'] == 'BUY' and t['symbol'] == symbol:
                            entry_price = t['price']
                            break
                    
                    profit = total_revenue - (quantity * entry_price) if entry_price else 0
                    profit_pct = (price - entry_price) / entry_price * 100 if entry_price and entry_price > 0 else 0
                    
                    # 记录交易
                    trade = {
                        'date': date_str,
                        'symbol': symbol,
                        'action': 'SELL',
                        'price': float(price),
                        'quantity': quantity,
                        'commission': float(commission),
                        'revenue': float(total_revenue),
                        'profit': float(profit),
                        'profit_pct': float(profit_pct),
                        'signal': float(signal),
                        'available_capital': float(available_capital),
                        'allocated_capital': float(allocated_capital)
                    }
                    trades.append(trade)
                    self.trades.append(trade)
            
            # 更新上一个信号
            last_signal = signal
        
        return trades
    
    def backtest(self, data=None):
        """
        回测策略，确保严格按照策略执行交易
        
        Args:
            data (pandas.DataFrame, optional): 市场数据，如果不提供则使用已设置的数据
            
        Returns:
            dict: 回测结果
        """
        if data is not None:
            self.set_data(data)
            
        if self.data is None or self.data.empty:
            raise ValueError("无法进行回测: 没有提供市场数据")
            
        # 确保数据已经排序
        self.data = self.data.sort_values('date').reset_index(drop=True)
        
        # 生成交易信号
        signals = self.generate_signals()
        
        # 执行交易
        self.initialize(self.initial_cash)
        trades = self.execute_trades(signals)
        
        # 计算每日权益曲线
        daily_equity = self._calculate_daily_equity()
        
        # 计算回撤
        drawdowns = None
        if daily_equity is not None and not daily_equity.empty:
            drawdowns = self._calculate_drawdowns(daily_equity)
            
        # 计算绩效指标
        performance = self.calculate_performance()
        
        return {
            'trades': trades,
            'performance': performance,
            'equity_curve': daily_equity.to_dict('records') if daily_equity is not None else None,
            'drawdowns': drawdowns.to_dict('records') if drawdowns is not None else None,
            'signals': signals.to_dict('records') if signals is not None else None
        }
    
    def calculate_performance(self):
        """
        计算策略绩效指标
        
        Returns:
            dict: 绩效指标
        """
        if not self.trades:
            return {
                'total_return': 0,
                'annual_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0
            }
            
        # 计算每日资产价值
        daily_equity = self._calculate_daily_equity()
        
        # 计算总收益率
        initial_equity = self.initial_cash
        final_equity = daily_equity.iloc[-1]['equity']
        total_return = (final_equity - initial_equity) / initial_equity * 100 if initial_equity > 0 else 0
        
        # 计算年化收益率
        days = (daily_equity.iloc[-1]['date'] - daily_equity.iloc[0]['date']).days
        if days <= 0:
            annual_return = 0
        else:
            annual_return = total_return * (365 / days)
        
        # 计算夏普比率
        daily_returns = daily_equity['equity'].pct_change().dropna()
        if len(daily_returns) > 0:
            sharpe_ratio = np.sqrt(252) * (daily_returns.mean() / daily_returns.std()) if daily_returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
            
        # 计算最大回撤
        drawdowns = self._calculate_drawdowns(daily_equity)
        max_drawdown = abs(drawdowns['drawdown'].min()) * 100 if not drawdowns.empty else 0
        
        # 计算胜率
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']
        win_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(win_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        return {
            'total_return': round(total_return, 2),
            'annual_return': round(annual_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'win_rate': round(win_rate, 2)
        }
    
    def _calculate_daily_equity(self):
        """
        计算每日资产价值
        
        Returns:
            pandas.DataFrame: 包含日期和资产价值的DataFrame
        """
        if self.data is None or self.data.empty:
            return pd.DataFrame(columns=['date', 'equity'])
            
        # 创建日期序列
        dates = pd.to_datetime(self.data['date'].unique())
        daily_equity = pd.DataFrame({'date': dates})
        daily_equity = daily_equity.sort_values('date')
        
        # 初始化持仓和现金状态
        equities = []
        positions = {}
        cash = self.initial_cash
        
        # 确保所有交易日期是datetime类型
        trades_df = pd.DataFrame(self.trades)
        if not trades_df.empty:
            trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        # 遍历每个交易日，计算资产价值
        for date in dates:
            # 获取当日价格
            day_data = self.data[self.data['date'] == date].copy()
            
            # 处理当日之前的所有交易
            if not trades_df.empty:
                day_trades = trades_df[trades_df['date'] <= date]
                
                # 重置状态
                positions = {}
                cash = self.initial_cash
                
                # 按时间顺序应用所有交易
                for _, trade in day_trades.iterrows():
                    symbol = trade['symbol']
                    if trade['action'] == 'BUY':
                        positions[symbol] = positions.get(symbol, 0) + trade['quantity']
                        cash -= trade['cost']
                    else:  # SELL
                        positions[symbol] = positions.get(symbol, 0) - trade['quantity']
                        cash += trade['revenue']
            
            # 计算持仓价值
            position_value = 0
            for symbol, quantity in positions.items():
                if quantity > 0 and not day_data.empty:
                    symbol_data = day_data
                    if 'symbol' in day_data.columns:
                        symbol_data = day_data[day_data['symbol'] == symbol]
                    
                    if not symbol_data.empty:
                        close_price = symbol_data['close'].iloc[0]
                        position_value += quantity * close_price
            
            # 计算总资产价值
            equity = cash + position_value
            equities.append(equity)
        
        daily_equity['equity'] = equities
        return daily_equity
    
    def _calculate_drawdowns(self, daily_equity):
        """
        计算回撤
        
        Args:
            daily_equity (pandas.DataFrame): 包含日期和资产价值的DataFrame
            
        Returns:
            pandas.DataFrame: 包含日期和回撤的DataFrame
        """
        if daily_equity is None or daily_equity.empty:
            return pd.DataFrame(columns=['date', 'drawdown'])
        
        # 计算峰值
        daily_equity['peak'] = daily_equity['equity'].cummax()
        
        # 计算回撤
        daily_equity['drawdown'] = (daily_equity['equity'] - daily_equity['peak']) / daily_equity['peak'].replace(0, 1e-9)
        
        # 返回日期和回撤
        return daily_equity[['date', 'drawdown']]