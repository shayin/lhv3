import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)

class StrategyBase:
    """策略基类，所有交易策略都应继承此类"""
    
    def __init__(self, params: Dict[str, Any] = None, name: str = "base_strategy"):
        """
        初始化策略
        
        Args:
            params: 策略参数字典
            name: 策略名称
        """
        # 检查params参数类型并记录日志
        if params is not None and not isinstance(params, dict):
            logger.error(f"StrategyBase.__init__: params参数类型错误，期望dict，实际为{type(params)}")
            params = {}  # 重置为空字典以避免后续错误
        
        self.params = params or {}
        self.parameters = self.params  # 兼容性别名
        self.name = name
        self.data = None  # 会在运行时设置
        self.initial_capital = 100000.0  # 默认初始资金
        self.strategy_logs = []  # 策略执行日志
        
        logger.info(f"初始化策略: {name}, 参数: {self.params}")

    def log(self, message: str, level: str = "INFO") -> None:
        """
        策略日志记录函数，供用户在策略中调用
        
        Args:
            message: 日志消息
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        """
        from datetime import datetime
        
        # 创建日志条目
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level.upper(),
            'message': str(message)
        }
        
        # 添加到策略日志列表
        self.strategy_logs.append(log_entry)
        
        # 同时输出到系统日志（便于调试）
        if level.upper() == "DEBUG":
            logger.debug(f"[策略日志] {message}")
        elif level.upper() == "WARNING":
            logger.warning(f"[策略日志] {message}")
        elif level.upper() == "ERROR":
            logger.error(f"[策略日志] {message}")
        else:
            logger.info(f"[策略日志] {message}")
    
    def get_logs(self) -> List[Dict[str, str]]:
        """
        获取策略执行日志
        
        Returns:
            日志列表
        """
        return self.strategy_logs.copy()
    
    def clear_logs(self) -> None:
        """清空策略日志"""
        self.strategy_logs.clear()

    def initialize(self, initial_capital: float = 100000.0) -> None:
        """
        初始化策略的初始资金
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        logger.info(f"初始化策略资金: {initial_capital}")
        
    def set_data(self, data: pd.DataFrame) -> None:
        """
        设置数据
        
        Args:
            data: 包含价格数据的DataFrame
        """
        self.data = data
        
    def generate_signals(self, data: pd.DataFrame = None) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: 包含价格数据的DataFrame，如果为None则使用self.data
            
        Returns:
            添加了信号列的DataFrame
        """
        if data is None:
            data = self.data
            
        if data is None or data.empty:
            return pd.DataFrame()
            
        raise NotImplementedError("子类必须实现generate_signals方法")
    
    def backtest(self, data: pd.DataFrame = None, initial_capital: float = None) -> Dict[str, Any]:
        """
        回测策略
        
        Args:
            data: 包含价格和信号的DataFrame，如果为None则使用self.data
            initial_capital: 初始资金，如果提供则覆盖self.initial_capital
            
        Returns:
            回测结果字典
        """
        logger.info(f"开始回测策略: {self.name}")
        
        # 如果提供了initial_capital，则更新实例变量
        if initial_capital is not None:
            self.initialize(initial_capital)
            
        # 使用实例变量作为初始资金
        initial_capital = self.initial_capital
        logger.info(f"初始资金: {initial_capital}")
        
        if data is None:
            data = self.data
            
        if data is None or data.empty:
            logger.error("没有数据可回测")
            return {'error': '没有数据可回测'}
            
        logger.info(f"回测数据: {len(data)}行, 从{data.index[0]}到{data.index[-1]}")
            
        # 生成信号
        if 'signal' not in data.columns:
            logger.info("数据中没有信号列，调用generate_signals生成信号")
            data = self.generate_signals(data)
            
        # 打印信号统计
        buy_signals = (data['signal'] == 1).sum()
        sell_signals = (data['signal'] == -1).sum()
        logger.info(f"信号统计: 买入信号 {buy_signals}个, 卖出信号 {sell_signals}个")
            
        # 临时修复：确保日期列是日期时间类型
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            # 设置日期为索引以便于后续处理
            data = data.set_index('date')
            
        # 初始化结果
        results = {}
        positions = pd.DataFrame(index=data.index).fillna(0.0)
        positions['position'] = 0
        returns = pd.DataFrame(index=data.index).fillna(0.0)
        
        # 计算持仓
        positions['position'] = data['signal'].shift(1)
        positions['position'].fillna(0, inplace=True)
        
        # 计算每日收益
        returns['price_change'] = data['close'].pct_change()
        returns['strategy'] = positions['position'] * returns['price_change']
        
        # 计算累计收益
        returns['cum_returns'] = (1 + returns['strategy']).cumprod()
        
        # 记录交易
        trades = []
        position = 0
        position_price = 0
        position_shares = 0
        position_date = None
        cash = initial_capital  # 初始现金
        total_equity = initial_capital  # 初始总资产
        
        logger.info("===== 交易明细 =====")
        logger.info(f"{'日期':<12} {'类型':<6} {'价格':<10} {'数量':<10} {'金额':<12} {'盈亏':<10} {'期初资金':<12} {'期末资金':<12}")
        logger.info("-" * 80)
        
        # 遍历每一行生成交易记录
        for date, row in data.iterrows():
            try:
                signal = row.get('signal', 0)
                
                if signal == 1 and position == 0:  # 买入信号
                    # 获取触发原因（如果有）
                    trigger_reason = row.get('trigger_reason', "未记录触发原因")
                    logger.info(f"执行买入操作 - 触发原因: {trigger_reason}")
                    
                    price = round(row['close'], 2)  # 价格精确到2位小数
                    # 将股数向下取整为整数
                    shares = int(cash / price)  # 使用当前现金计算可买入的股数
                    if shares <= 0:
                        logger.warning(f"资金不足无法买入: 当前资金{cash}元，股价{price}元")
                        continue  # 资金不足，跳过本次交易
                        
                    actual_cost = round(shares * price, 2)  # 实际花费精确到2位小数
                    
                    # 计算交易前后的资金状况
                    before_cash = cash  # 交易前现金
                    before_equity = total_equity  # 交易前总资产
                    
                    cash -= actual_cost  # 更新现金
                    total_equity = cash + (shares * price)  # 更新总资产
                    
                    after_cash = cash  # 交易后现金
                    after_equity = total_equity  # 交易后总资产
                    
                    position_price = price  # 记录买入价格
                    position_shares = shares  # 记录买入股数
                    position_date = date  # 记录买入日期，用于计算持仓天数
                    trade_date = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
                    
                    trade = {
                        'date': trade_date,
                        'action': 'BUY',
                        'price': float(price),
                        'shares': int(shares),  # 确保股数是整数
                        'value': float(actual_cost),
                        'entry_price': float(price),  # 添加入场价格字段
                        'before_cash': round(before_cash, 2),  # 交易前现金
                        'after_cash': round(after_cash, 2),  # 交易后现金
                        'before_equity': round(before_equity, 2),  # 交易前总资产
                        'after_equity': round(after_equity, 2),  # 交易后总资产
                        'trigger_reason': trigger_reason  # 添加触发原因
                    }
                    trades.append(trade)
                    position = 1
                    
                    # 打印交易明细
                    logger.info(f"{trade_date:<12} {'买入':<6} {price:<10.2f} {shares:<10d} {actual_cost:<12.2f} {'':<10} {before_cash:<12.2f} {after_cash:<12.2f}")

                elif signal == -1 and position == 1:  # 卖出信号
                    # 获取触发原因（如果有）
                    trigger_reason = row.get('trigger_reason', "未记录触发原因")
                    logger.info(f"执行卖出操作 - 触发原因: {trigger_reason}")
                    
                    price = round(row['close'], 2)  # 价格精确到2位小数
                    shares = position_shares  # 使用之前买入的实际股数
                    sale_value = round(shares * price, 2)  # 卖出总值精确到2位小数
                    profit = round(sale_value - (shares * position_price), 2)  # 计算盈亏精确到2位小数
                    profit_percent = round((price - position_price) / position_price * 100, 2)  # 计算百分比收益率精确到2位小数
                    
                    # 计算交易前后的资金状况
                    before_cash = cash  # 交易前现金
                    before_equity = cash + (shares * position_price)  # 交易前总资产
                    
                    cash += sale_value  # 更新现金
                    total_equity = cash  # 更新总资产
                    
                    after_cash = cash  # 交易后现金
                    after_equity = total_equity  # 交易后总资产
                    
                    # 计算持仓天数
                    holding_days = 0
                    if hasattr(date, 'to_pydatetime') and hasattr(position_date, 'to_pydatetime'):
                        holding_days = (date.to_pydatetime() - position_date.to_pydatetime()).days
                    elif hasattr(date, 'date') and hasattr(position_date, 'date'):
                        holding_days = (date.date() - position_date.date()).days
                    else:
                        try:
                            # 尝试转换为日期格式再计算
                            d1 = pd.to_datetime(date)
                            d2 = pd.to_datetime(position_date)
                            holding_days = (d1 - d2).days
                        except:
                            holding_days = 0
                    
                    # 确保持仓天数至少为1天
                    holding_days = max(1, holding_days)
                    
                    trade_date = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
                    
                    trade = {
                        'date': trade_date,
                        'action': 'SELL',
                        'price': float(price),
                        'shares': int(shares),  # 确保股数是整数
                        'value': float(sale_value),
                        'profit': float(profit),
                        'profit_percent': float(profit_percent),  # 添加百分比收益率
                        'entry_price': float(position_price),  # 添加入场价格
                        'holding_days': int(holding_days),  # 添加持仓天数
                        'before_cash': round(before_cash, 2),  # 交易前现金
                        'after_cash': round(after_cash, 2),  # 交易后现金
                        'before_equity': round(before_equity, 2),  # 交易前总资产
                        'after_equity': round(after_equity, 2),  # 交易后总资产
                        'trigger_reason': trigger_reason  # 添加触发原因
                    }
                    trades.append(trade)
                    position = 0
                    
                    # 打印交易明细
                    logger.info(f"{trade_date:<12} {'卖出':<6} {price:<10.2f} {shares:<10d} {sale_value:<12.2f} {profit:<10.2f} {before_cash:<12.2f} {after_cash:<12.2f}")
                    
            except Exception as e:
                logger.error(f"处理交易数据时出错: {e}, 日期: {date}, 行数据: {row}")
        
        logger.info("=" * 80)
        
        # 计算策略指标
        results['trades'] = trades
        
        # 转换returns为可JSON序列化格式
        returns_dict = {
            'date': [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in returns.index],
            'price_change': returns['price_change'].fillna(0).tolist(),
            'strategy': returns['strategy'].fillna(0).tolist(),
            'cum_returns': returns['cum_returns'].fillna(1).tolist()
        }
        results['returns'] = returns_dict
        
        # 转换positions为可JSON序列化格式
        positions_dict = {
            'date': [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in positions.index],
            'position': positions['position'].tolist()
        }
        results['positions'] = positions_dict
        
        # 计算Sharpe比率
        strategy_returns = returns['strategy'].dropna()
        if len(strategy_returns) > 0 and strategy_returns.std() != 0:
            sharpe = float(strategy_returns.mean() / strategy_returns.std() * np.sqrt(252))
            results['sharpe'] = sharpe
            logger.info(f"Sharpe比率: {sharpe:.4f}")
        else:
            results['sharpe'] = 0.0
            logger.info("Sharpe比率: 0.0 (标准差为0或没有足够的数据)")
        
        # 计算总收益率
        total_return = 0.0
        if len(returns) > 0 and 'cum_returns' in returns.columns:
            final_return = returns['cum_returns'].dropna()
            if len(final_return) > 0:
                final_value = final_return.iloc[-1]
                total_return = float((final_value - 1) * 100)  # 百分比
                results['total_return'] = total_return
                logger.info(f"总收益率: {total_return:.2f}%")
            else:
                results['total_return'] = 0.0
                logger.info("总收益率: 0.0% (没有有效的累计收益数据)")
        else:
            results['total_return'] = 0.0
            logger.info("总收益率: 0.0% (没有足够的数据)")
            
        # 计算年化收益率
        annual_return = 0.0
        if len(returns) > 1:
            daily_return = strategy_returns.mean()
            annual_return = float(daily_return * 252 * 100)  # 年化百分比
            results['annual_return'] = annual_return
            logger.info(f"年化收益率: {annual_return:.2f}%")
        else:
            results['annual_return'] = 0.0
            logger.info("年化收益率: 0.0% (没有足够的数据)")
            
        # 计算最大回撤
        max_drawdown = 0.0
        cum_returns = returns['cum_returns'].fillna(1)
        if len(cum_returns) > 0:
            # 计算累积最大值
            running_max = cum_returns.cummax()
            # 计算相对回撤
            drawdown = (cum_returns / running_max - 1) * 100
            # 最大回撤值
            max_drawdown = drawdown.min()
            results['max_drawdown'] = float(max_drawdown)
            logger.info(f"最大回撤: {max_drawdown:.2f}%")
            
            # 添加回撤数据
            drawdown_dict = {
                'date': [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in drawdown.index],
                'drawdown': drawdown.tolist()
            }
            results['drawdowns'] = drawdown_dict
        else:
            results['max_drawdown'] = 0.0
            logger.info("最大回撤: 0.0% (没有足够的数据)")
        
        # 计算胜率
        win_rate = 0.0
        if trades:
            winning_trades = sum(1 for trade in trades if trade.get('action') == 'SELL' and trade.get('profit', 0) > 0)
            total_sell_trades = sum(1 for trade in trades if trade.get('action') == 'SELL')
            if total_sell_trades > 0:
                win_rate = float(winning_trades / total_sell_trades * 100)
                results['win_rate'] = win_rate
                logger.info(f"胜率: {win_rate:.2f}% ({winning_trades}/{total_sell_trades})")
            else:
                results['win_rate'] = 0.0
                logger.info("胜率: 0.0% (没有卖出交易)")
        else:
            results['win_rate'] = 0.0
            logger.info("胜率: 0.0% (没有交易记录)")
        
        # 直接计算总收益率，使用最终资金与初始资金
        final_equity = 0.0
        
        # 如果有未平仓持仓，则添加到最终资金
        if position == 1:  # 如果回测结束时还有持仓
            # 使用最后一个交易日的收盘价计算持仓价值
            last_close_price = data['close'].iloc[-1]
            position_value = position_shares * last_close_price
            final_equity = cash + position_value
        else:
            # 如果没有持仓，最终资金就是现金
            final_equity = cash
        
        # 如果有交易，使用交易后现金计算收益率
        if trades and len(trades) > 0:
            # 检查是否有卖出交易
            sell_trades = [t for t in trades if t.get('action') == 'SELL']
            if sell_trades:
                # 找出最新的交易记录
                latest_trade = trades[-1]
                # 更新最终资金
                if latest_trade.get('action') == 'SELL':
                    # 如果最后一笔是卖出，用卖出后现金作为最终权益
                    final_equity = latest_trade.get('after_cash', cash)
                elif latest_trade.get('action') == 'BUY':
                    # 如果最后一笔是买入，需要加上持仓价值
                    position_value = latest_trade.get('shares', 0) * data['close'].iloc[-1]
                    final_equity = latest_trade.get('after_cash', cash) + position_value
                    
        # 计算总收益率
        total_return = ((final_equity - initial_capital) / initial_capital) * 100
        results['total_return'] = round(total_return, 2)
        logger.info(f"更新计算总收益率: {total_return:.2f}% (初始资金: {initial_capital:.2f}, 最终资金: {final_equity:.2f})")
        
        # 计算年化收益率
        if len(returns) > 1:
            # 获取第一个和最后一个交易日
            first_date = pd.to_datetime(returns.index[0])
            last_date = pd.to_datetime(returns.index[-1])
            # 计算交易天数
            trading_days = (last_date - first_date).days
            # 避免除以零
            if trading_days > 0:
                # 计算年化收益率
                annual_return = total_return * (365 / trading_days)
                results['annual_return'] = round(annual_return, 2)
                logger.info(f"更新计算年化收益率: {annual_return:.2f}% (交易天数: {trading_days}天)")
            else:
                results['annual_return'] = 0.0
                logger.info("年化收益率: 0.0% (交易天数为0)")
        else:
            results['annual_return'] = 0.0
            logger.info("年化收益率: 0.0% (没有足够的数据)")
        
        # 更新性能指标
        performance = {
            'total_return': round(results['total_return'], 2),
            'annual_return': round(results['annual_return'], 2),
            'sharpe_ratio': round(results['sharpe'], 2),
            'max_drawdown': round(results['max_drawdown'], 2),
            'win_rate': round(results['win_rate'], 2),
            'profit_factor': round(results.get('profit_factor', 0), 2)
        }
        results['performance'] = performance
        
        # 交易统计信息
        if trades:
            num_trades = len(trades)
            num_buy = sum(1 for trade in trades if trade.get('action') == 'BUY')
            num_sell = sum(1 for trade in trades if trade.get('action') == 'SELL')
            
            # 计算平均持仓时间
            if num_buy > 0 and num_sell > 0:
                holding_periods = []
                buy_dates = {}
                
                for trade in trades:
                    date = trade.get('date')
                    action = trade.get('action')
                    
                    if action == 'BUY':
                        buy_dates[len(buy_dates)] = date
                    elif action == 'SELL' and buy_dates:
                        buy_date = buy_dates.pop(max(buy_dates.keys()))
                        try:
                            buy_dt = pd.to_datetime(buy_date)
                            sell_dt = pd.to_datetime(date)
                            days = (sell_dt - buy_dt).days
                            holding_periods.append(days)
                        except:
                            pass
                
                if holding_periods:
                    avg_holding = sum(holding_periods) / len(holding_periods)
                    logger.info(f"平均持仓时间: {avg_holding:.2f}天")
            
            # 计算总盈利和总亏损
            total_profit = sum(trade.get('profit', 0) for trade in trades if trade.get('action') == 'SELL' and trade.get('profit', 0) > 0)
            total_loss = sum(trade.get('profit', 0) for trade in trades if trade.get('action') == 'SELL' and trade.get('profit', 0) < 0)
            
            logger.info(f"交易统计: 总交易 {num_trades}次, 买入 {num_buy}次, 卖出 {num_sell}次")
            logger.info(f"盈亏统计: 总盈利 {total_profit:.2f}, 总亏损 {total_loss:.2f}, 净盈亏 {total_profit + total_loss:.2f}")
            
            # 计算盈亏比
            if total_loss != 0:
                profit_loss_ratio = round(abs(total_profit / total_loss), 2)
                logger.info(f"盈亏比: {profit_loss_ratio:.2f}")
                results['profit_factor'] = profit_loss_ratio  # 添加盈亏比到结果中
            else:
                results['profit_factor'] = 0.0  # 如果没有亏损交易，设置为0
            
        # 添加信号数据
        if 'signal' in data.columns:
            signals_data = []
            for date, row in data.iterrows():
                if row['signal'] != 0:
                    signal_type = 'buy' if row['signal'] == 1 else 'sell'
                    signal_date = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
                    signals_data.append({
                        'date': signal_date,
                        'type': signal_type,
                        'price': round(float(row['close']), 2),
                        'signal': int(row['signal'])
                    })
            results['signals'] = signals_data
        
        # 添加K线数据，用于前端显示
        kline_data = []
        for date, row in data.iterrows():
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            kline_data.append({
                'date': date_str,
                'open': round(float(row.get('open', row.get('close', 0))), 2),
                'close': round(float(row.get('close', 0)), 2),
                'high': round(float(row.get('high', row.get('close', 0))), 2),
                'low': round(float(row.get('low', row.get('close', 0))), 2),
                'volume': float(row.get('volume', 0))
            })
        results['kline_data'] = kline_data
            
        logger.info(f"回测完成: {self.name}, 总收益率: {total_return:.2f}%, 年化收益率: {annual_return:.2f}%, Sharpe比率: {results['sharpe']:.4f}, 最大回撤: {max_drawdown:.2f}%, 胜率: {win_rate:.2f}%")
        
        # 添加策略日志到结果中
        results['logs'] = self.get_logs()

        # 更新权益曲线 - 跟踪每次交易后的实际资金变化
        if trades:
            # 创建交易日期到权益的映射
            trade_equity = {}
            
            # 记录每次交易后的权益
            for trade in trades:
                trade_date = trade.get('date')
                # 转换为datetime，用于索引
                try:
                    dt = pd.to_datetime(trade_date)
                    # 用交易后的总资产更新
                    if dt in returns.index:
                        trade_equity[dt] = float(trade.get('after_equity', 0))
                except:
                    logger.warning(f"无法解析交易日期: {trade_date}")
            
            # 按时间顺序排序交易
            sorted_dates = sorted(trade_equity.keys())
            
            # 获取初始日期和结束日期
            start_date = returns.index[0]
            end_date = returns.index[-1]
            
            # 填充权益曲线 - 考虑每日股票价值变化
            previous_trade_date = None
            previous_position = 0
            previous_position_shares = 0
            previous_position_price = 0
            previous_cash = initial_capital
            
            # 记录初始值
            returns.loc[returns.index[0], 'cum_returns'] = initial_capital
            
            # 按时间顺序处理每个交易日
            for date in returns.index:
                # 如果是交易日，更新当前持仓和现金状态
                if date in trade_equity:
                    current_equity = trade_equity[date]
                    returns.loc[date, 'cum_returns'] = current_equity
                    
                    # 找到对应的交易
                    for trade in trades:
                        try:
                            trade_date = pd.to_datetime(trade.get('date'))
                            if trade_date == date:
                                # 更新当前状态
                                if trade.get('action') == 'BUY':
                                    previous_position = 1
                                    previous_position_shares = trade.get('shares', 0)
                                    previous_position_price = trade.get('price', 0)
                                    previous_cash = trade.get('after_cash', previous_cash)
                                elif trade.get('action') == 'SELL':
                                    previous_position = 0
                                    previous_position_shares = 0
                                    previous_cash = trade.get('after_cash', previous_cash)
                                
                                previous_trade_date = date
                                break
                        except:
                            pass
                
                # 非交易日但有持仓，根据当日价格计算权益
                elif previous_position == 1 and previous_position_shares > 0:
                    # 使用当日收盘价计算持仓价值
                    current_price = data.loc[date, 'close']
                    position_value = previous_position_shares * current_price
                    
                    # 当日总资产 = 现金 + 持仓价值
                    daily_equity = previous_cash + position_value
                    returns.loc[date, 'cum_returns'] = daily_equity
                
                # 非交易日且无持仓，权益等于现金
                else:
                    returns.loc[date, 'cum_returns'] = previous_cash
            
            # 如果最后一笔是买入，需要考虑未平仓的持仓价值（这部分可以保留，提供额外保障）
            if position == 1:
                # 获取最后一个有交易的日期
                last_date = sorted_dates[-1] if sorted_dates else start_date
                last_idx = returns.index.get_loc(last_date)
                
                # 确保该日期之后的所有日期都正确计算了持仓价值
                for i in range(last_idx, len(returns)):
                    date = returns.index[i]
                    
                    # 只有在持有期间才更新价值
                    if position == 1 and position_shares > 0:
                        price = data.loc[date, 'close']
                        position_value = position_shares * price
                        
                        # 确保不重复计算现金
                        if date in trade_equity:
                            # 使用交易日记录的权益值
                            continue
                        else:
                            # 非交易日，现金不变，股票价值更新
                            cash_value = cash
                            returns.loc[date, 'cum_returns'] = cash_value + position_value
            
            # 转换returns为可JSON序列化格式
            returns_dict = {
                'date': [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in returns.index],
                'price_change': returns['price_change'].fillna(0).tolist(),
                'strategy': returns['strategy'].fillna(0).tolist(),
                'cum_returns': returns['cum_returns'].fillna(1).tolist()
            }
            results['returns'] = returns_dict
            
            # 转换equity_curve为可JSON序列化格式
            equity_curve_dict = {
                'date': [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in returns.index],
                'equity': returns['cum_returns'].fillna(1).tolist()
            }
            results['equity_curve'] = equity_curve_dict
            
            # 输出权益曲线样本用于调试
            num_samples = min(5, len(returns))
            logger.info(f"权益曲线样本(前{num_samples}条): {returns.head(num_samples)}")
            logger.info(f"权益曲线样本(后{num_samples}条): {returns.tail(num_samples)}")
        else:
            # 如果没有交易，返回一个只有初始资金的平坦曲线
            dates = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in returns.index]
            equities = [initial_capital] * len(dates)
            results['equity_curve'] = {'date': dates, 'equity': equities}
        
        return results 