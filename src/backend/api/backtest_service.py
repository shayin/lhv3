import logging
import pandas as pd
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session

from ..models.market_data import Stock, DailyPrice
from ..models.data_models import Stock as StockModel, StockData
from ..data.fetcher import DataFetcher
from ..data.processor import DataProcessor
from ..backtest.engine import BacktestEngine
from ..utils.cache import backtest_cache
from ..strategy.templates.ma_crossover_strategy import MACrossoverStrategy as MovingAverageCrossover
# 暂时注释掉不存在的导入，等文件创建后再启用
# from ..strategy.templates.bollinger_bands import BollingerBandsStrategy
# from ..strategy.templates.macd import MACDStrategy
# from ..strategy.templates.rsi import RSIStrategy

logger = logging.getLogger(__name__)

class BacktestService:
    """回测服务，提供回测相关的功能"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化回测服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.data_fetcher = DataFetcher()
        self.data_processor = DataProcessor()
    
    def get_backtest_data(self, 
                         symbol: str, 
                         start_date: str, 
                         end_date: Optional[str] = None, 
                         data_source: str = "database", 
                         features: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取回测所需的市场数据
        
        Args:
            symbol: 交易品种代码
            start_date: 开始日期
            end_date: 结束日期，如果为None则使用当前日期
            data_source: 数据来源，可以是 "database"(从数据库获取) 或 "yahoo"/"akshare"(从外部获取)
            features: 需要添加的技术指标列表
            
        Returns:
            pandas.DataFrame: 包含市场数据的DataFrame
        """
        logger.info(f"获取回测数据: symbol={symbol}, 日期={start_date}至{end_date}, 来源={data_source}")
        
        # 设置默认结束日期
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # 如果数据来源是数据库
        if data_source.lower() == "database" and self.db is not None:
            logger.info(f"从数据库获取回测数据: {symbol}")
            try:
                return self._get_data_from_database(symbol, start_date, end_date, features)
            except Exception as e:
                logger.error(f"从数据库获取数据失败: {e}")
                # 不再尝试从外部获取数据，而是直接返回空的DataFrame
                logger.warning(f"数据库中找不到 {symbol} 的数据，返回空数据集")
                return pd.DataFrame()
        else:
            # 如果显式指定使用外部数据源，仍然从外部获取
            if data_source.lower() != "database":
                return self._get_data_from_external(symbol, start_date, end_date, data_source, features)
            else:
                logger.warning("数据库未初始化或无效，返回空数据集")
                return pd.DataFrame()
    
    def _get_data_from_database(self, 
                               symbol: str, 
                               start_date: str, 
                               end_date: str, 
                               features: Optional[List[str]] = None) -> pd.DataFrame:
        """
        从数据库获取回测数据
        
        Args:
            symbol: 交易品种代码
            start_date: 开始日期
            end_date: 结束日期
            features: 需要添加的技术指标列表
            
        Returns:
            pandas.DataFrame: 包含市场数据的DataFrame
        """
        if self.db is None:
            raise ValueError("数据库会话未初始化")
            
        logger.debug(f"开始从数据库查询数据: symbol={symbol}, 日期范围={start_date}至{end_date}")
        
        # 查询股票ID - 使用 StockModel 代替 Stock
        stock = self.db.query(StockModel).filter(StockModel.symbol == symbol).first()
        if not stock:
            logger.warning(f"数据库中未找到股票: {symbol}")
            return pd.DataFrame()
            
        logger.debug(f"找到股票: {stock.name} (ID: {stock.id})")
        
        # 查询股票价格数据 - 使用 StockData 代替 DailyPrice
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        query = self.db.query(StockData).filter(
            StockData.stock_id == stock.id,
            StockData.date >= start_date_obj,
            StockData.date <= end_date_obj
        ).order_by(StockData.date)
        
        stock_data = query.all()
        logger.debug(f"查询到价格数据记录数: {len(stock_data)}")
        
        if not stock_data:
            logger.warning(f"数据库中未找到{symbol}在{start_date}至{end_date}之间的价格数据")
            return pd.DataFrame()
            
        # 将查询结果转换为DataFrame，注意字段名称可能有所不同
        data = pd.DataFrame([{
            'date': data_point.date,
            'open': data_point.open,
            'high': data_point.high,
            'low': data_point.low,
            'close': data_point.close,
            'volume': data_point.volume,
            'adjusted_close': data_point.adj_close  # StockData 使用 adj_close 而不是 adjusted_close
        } for data_point in stock_data])
        
        # 处理数据并添加特征
        if not data.empty and features:
            logger.debug(f"处理数据并添加特征: {features}")
            data = self.data_processor.process_data(data, features)
            
        return data
    
    def _get_data_from_external(self, 
                               symbol: str, 
                               start_date: str, 
                               end_date: str, 
                               data_source: str, 
                               features: Optional[List[str]] = None) -> pd.DataFrame:
        """
        从外部数据源获取回测数据
        
        Args:
            symbol: 交易品种代码
            start_date: 开始日期
            end_date: 结束日期
            data_source: 数据来源，如 "yahoo", "akshare"
            features: 需要添加的技术指标列表
            
        Returns:
            pandas.DataFrame: 包含市场数据的DataFrame
        """
        logger.info(f"从外部数据源获取数据: {data_source}")
        
        # 获取原始数据
        raw_data = self.data_fetcher.fetch_data(symbol, start_date, end_date, data_source)
        if raw_data is None or raw_data.empty:
            logger.error(f"无法获取{symbol}的数据")
            return pd.DataFrame()
            
        logger.info(f"获取到原始数据，行数: {len(raw_data)}")
        
        # 处理数据并添加特征
        processed_data = self.data_processor.process_data(raw_data, features)
        if processed_data is None or processed_data.empty:
            logger.error(f"处理{symbol}的数据失败")
            return pd.DataFrame()
            
        return processed_data
    
    def _generate_backtest_cache_key(self, strategy_id: Union[str, int], symbol: str, 
                                   start_date: str, end_date: Optional[str], 
                                   initial_capital: float, commission_rate: float, 
                                   slippage_rate: float, parameters: Optional[Dict[str, Any]]) -> str:
        """生成回测缓存键"""
        key_data = {
            'strategy_id': str(strategy_id),
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date or '',
            'initial_capital': initial_capital,
            'commission_rate': commission_rate,
            'slippage_rate': slippage_rate,
            'parameters': parameters or {}
        }
        key_str = str(sorted(key_data.items()))
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _generate_data_hash(self, data: pd.DataFrame) -> str:
        """生成数据哈希用于缓存验证"""
        if data.empty:
            return ""
        # 使用数据的形状、列名和前几行数据生成哈希
        hash_data = f"{data.shape}_{list(data.columns)}_{data.head().to_string()}"
        return hashlib.md5(hash_data.encode()).hexdigest()

    def run_backtest(self, 
                    strategy_id: Union[str, int], 
                    symbol: str, 
                    start_date: str, 
                    end_date: Optional[str] = None, 
                    initial_capital: float = 100000.0,
                    commission_rate: float = 0.0015,
                    slippage_rate: float = 0.001,
                    data_source: str = "database",
                    parameters: Optional[Dict[str, Any]] = None,
                    features: Optional[List[str]] = None,
                    force_refresh: bool = False) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            strategy_id: 策略ID或策略名称
            symbol: 交易品种代码
            start_date: 开始日期
            end_date: 结束日期，如果为None则使用当前日期
            initial_capital: 初始资金
            commission_rate: 手续费率
            slippage_rate: 滑点率
            data_source: 数据来源
            parameters: 策略参数，包含仓位配置(positionConfig)等
            features: 需要添加的技术指标列表
            
        Returns:
            Dict[str, Any]: 回测结果
        """
        # 生成缓存键
        cache_key = self._generate_backtest_cache_key(
            strategy_id, symbol, start_date, end_date, 
            initial_capital, commission_rate, slippage_rate, parameters
        )
        
        logger.info("=" * 80)
        logger.info(f"开始回测: 策略={strategy_id}, 品种={symbol}, 日期={start_date}至{end_date}")
        logger.info(f"参数: 初始资金={initial_capital}, 手续费率={commission_rate}, 滑点率={slippage_rate}")
        logger.info(f"缓存键: {cache_key}")
        
        # 1. 获取回测数据
        stock_data = self.get_backtest_data(symbol, start_date, end_date, data_source, features)
        if stock_data.empty:
            error_msg = f"无法获取回测数据: {symbol}, {start_date}至{end_date}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "data": None
            }
            
        logger.info(f"获取到回测数据，行数: {len(stock_data)}")
        
        # 生成数据哈希
        data_hash = self._generate_data_hash(stock_data)
        
        # 检查缓存（如果不是强制刷新）
        if not force_refresh:
            cached_result = backtest_cache.get(cache_key, data_hash)
            if cached_result is not None:
                logger.info("使用缓存的回测结果")
                return {
                    "status": "success",
                    "message": "回测完成（使用缓存）",
                    "data": cached_result
                }
        else:
            # 强制刷新时，删除现有缓存
            logger.info("强制刷新：删除现有缓存")
            backtest_cache.delete(cache_key, data_hash)
        
        # 2. 实例化策略
        # 提取策略参数：如果parameters中有parameters字段，则使用它；否则使用整个parameters对象
        strategy_params = parameters.get('parameters', {}) if parameters else {}
        logger.info(f"提取到的策略参数: {strategy_params}")
        strategy = self._get_strategy_instance(strategy_id, stock_data, strategy_params)
        if strategy is None:
            error_msg = f"无法创建策略实例: {strategy_id}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "data": None
            }
            
        # 3. 创建回测引擎
        engine = BacktestEngine(
            strategy=strategy,
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
            start_date=start_date,
            end_date=end_date
        )
        
        # 4. 设置仓位配置参数到回测引擎
        if parameters:
            engine.set_parameters(parameters)
            logger.info("仓位配置参数已传递给回测引擎")
        
        # 5. 运行回测
        try:
            result = engine.run(stock_data)
            logger.info(f"回测完成: 总收益率={result['total_return']:.2%}, 最大回撤={result['max_drawdown']:.2%}")
            
            # 缓存回测结果
            backtest_cache.set(cache_key, result, data_hash)
            logger.info("回测结果已缓存")
            
            # 6. 保存回测结果（如果需要）
            if parameters and parameters.get('save_backtest', False):
                try:
                    self._save_backtest_result(
                        strategy_id=strategy_id,
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        initial_capital=initial_capital,
                        parameters=parameters,
                        result=result,
                        backtest_name=parameters.get('backtest_name'),
                        backtest_description=parameters.get('backtest_description')
                    )
                    logger.info("回测结果已保存")
                except Exception as e:
                    logger.error(f"保存回测结果失败: {e}")
            
            # 7. 添加保存标识到结果中
            result['saved'] = parameters.get('save_backtest', False)
            
            return {
                "status": "success",
                "message": "回测完成",
                "data": result
            }
        except Exception as e:
            error_msg = f"回测执行失败: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "data": None
            }
    
    def _get_strategy_instance(self, 
                              strategy_id: Union[str, int], data: pd.DataFrame = None, 
                              parameters: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        根据策略ID创建策略实例
        
        Args:
            strategy_id: 策略ID或策略名称
            parameters: 策略参数
            
        Returns:
            策略实例
        """
        if parameters is None:
            parameters = {}
            
        # 首先检查是否为数字ID（整数或字符串形式的数字）
        if self.db is not None and (isinstance(strategy_id, int) or (isinstance(strategy_id, str) and strategy_id.isdigit())):
            try:
                from ..models.strategy import Strategy as StrategyModel
                from ..api.strategy_routes import load_strategy_from_code
                
                # 转换字符串ID为整数
                if isinstance(strategy_id, str):
                    strategy_id = int(strategy_id)
                
                db_strategy = self.db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
                if not db_strategy:
                    logger.error(f"数据库中未找到ID为{strategy_id}的策略")
                    return None
                    
                logger.info(f"从数据库加载策略: {db_strategy.name} (ID: {strategy_id})")
                
                # 如果未提供参数，使用策略默认参数
                if not parameters and db_strategy.parameters:
                    try:
                        import json
                        parameters = json.loads(db_strategy.parameters)
                        logger.info(f"使用策略默认参数: {parameters}")
                    except:
                        logger.warning(f"解析策略默认参数失败")
                
                # 导入必要的模块，确保策略代码中的相对导入能够正常工作
                try:
                    # 使用正确的导入路径，包含templates文件夹
                    import src.backend.strategy.templates.strategy_template
                    import src.backend.strategy.templates.ma_crossover_strategy
                    
                    # 记录导入路径，用于调试
                    logger.debug(f"成功导入策略模板，路径: {src.backend.strategy.templates.strategy_template.__file__}")
                    
                    # 创建导入上下文
                    globals_dict = {
                        '__name__': '__main__',
                        '__file__': '__tmp_strategy__',
                        'StrategyTemplate': src.backend.strategy.templates.strategy_template.StrategyTemplate,
                        'pd': __import__('pandas'),
                        'np': __import__('numpy')
                    }
                    
                    # 确保 db_strategy.code 为字符串（有时 DB 存储为 bytes）
                    strategy_code = db_strategy.code
                    if isinstance(strategy_code, bytes):
                        strategy_code = strategy_code.decode('utf-8')
                    
                    # 预览策略代码（用于调试）
                    logger.debug(f"策略代码预览: {strategy_code[:200]}...")
                    
                    # 加载策略
                    strategy_instance = load_strategy_from_code(strategy_code, parameters)
                    
                    if strategy_instance and data is not None:
                        strategy_instance.set_data(data)
                    
                    return strategy_instance
                    
                except ImportError as e:
                    logger.error(f"导入策略模块失败: {e}")
                    return None
                except Exception as e:
                    logger.error(f"加载策略失败: {e}")
                    return None
                    
            except Exception as e:
                logger.error(f"创建策略实例时发生错误: {e}")
                return None
        
        # 如果是字符串策略ID，根据名称创建实例
        elif isinstance(strategy_id, str):
            if strategy_id == "ma_crossover":
                logger.info(f"创建策略: 移动平均线交叉策略, 参数: {parameters}")
                strategy = MovingAverageCrossover(parameters=parameters)
                if data is not None:
                    strategy.set_data(data)
                return strategy
            # 以下策略暂时注释掉，等实现后再启用
            # elif strategy_id == "bollinger_bands":
            #     logger.info(f"创建策略: 布林带策略, 参数: {parameters}")
            #     return BollingerBandsStrategy(parameters=parameters)
            # elif strategy_id == "macd":
            #     logger.info(f"创建策略: MACD策略, 参数: {parameters}")
            #     return MACDStrategy(parameters=parameters)
            # elif strategy_id == "rsi":
            #     logger.info(f"创建策略: RSI策略, 参数: {parameters}")
            #     return RSIStrategy(parameters=parameters)
            else:
                logger.error(f"未知的策略ID: {strategy_id}")
                return None
        
        logger.error(f"无法创建策略实例: {strategy_id}")
        return None
    
    def _prepare_full_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备完整的参数信息，包括策略参数
        
        Args:
            parameters: 原始参数对象
            
        Returns:
            包含策略参数的完整参数对象
        """
        if not parameters:
            return {}
            
        strategy_params = parameters.get('parameters', {})
        full_parameters = parameters.copy()
        full_parameters['strategy_parameters'] = strategy_params
        return full_parameters
    
    def _save_backtest_result(self, 
                            strategy_id: Union[str, int],
                            symbol: str,
                            start_date: str,
                            end_date: str,
                            initial_capital: float,
                            parameters: Dict[str, Any],
                            result: Dict[str, Any],
                            backtest_name: Optional[str] = None,
                            backtest_description: Optional[str] = None) -> None:
        """
        保存回测结果到新架构数据库
        
        Args:
            strategy_id: 策略ID或策略名称
            symbol: 交易品种代码
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            parameters: 策略参数
            result: 回测结果
        """
        if self.db is None:
            logger.warning("数据库会话未初始化，无法保存回测结果")
            return
        
        try:
            from ..models import Strategy, StrategySnapshot, Backtest, BacktestStatus, BacktestHistory
            
            # 1. 获取策略信息
            strategy = None
            if isinstance(strategy_id, int):
                strategy = self.db.query(Strategy).filter(Strategy.id == strategy_id).first()
            else:
                strategy = self.db.query(Strategy).filter(Strategy.name == strategy_id).first()
            
            # 2. 创建策略快照
            strategy_snapshot = None
            if strategy:
                strategy_snapshot = StrategySnapshot(
                    strategy_id=strategy.id,
                    name=strategy.name,
                    description=strategy.description,
                    code=strategy.code,
                    parameters=strategy.parameters,
                    template=strategy.template
                )
                self.db.add(strategy_snapshot)
                self.db.flush()  # 获取ID
            
            # 3. 生成回测名称
            if not backtest_name:
                backtest_name = f"{symbol}_{start_date}_{end_date}"
                if strategy:
                    backtest_name = f"{strategy.name}_{symbol}_{start_date}_{end_date}"
            
            # 4. 检查是否已存在同名的回测状态
            existing_status = self.db.query(BacktestStatus).filter(BacktestStatus.name == backtest_name).first()
            
            if existing_status:
                # 更新现有状态记录
                existing_status.description = backtest_description or f"回测: {symbol} ({start_date} 至 {end_date})"
                existing_status.strategy_id = strategy.id if strategy else None
                existing_status.strategy_snapshot_id = strategy_snapshot.id if strategy_snapshot else existing_status.strategy_snapshot_id
                existing_status.start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                existing_status.end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                existing_status.initial_capital = initial_capital
                existing_status.instruments = [symbol]
                # 保存完整的参数信息，包括策略参数
                existing_status.parameters = self._prepare_full_parameters(parameters)
                existing_status.position_config = parameters.get('positionConfig')
                # 保存回测结果数据
                existing_status.results = result
                existing_status.equity_curve = result.get('equity_curve')
                existing_status.trade_records = result.get('trade_records')
                existing_status.performance_metrics = {
                    'total_return': result.get('total_return'),
                    'max_drawdown': result.get('max_drawdown'),
                    'sharpe_ratio': result.get('sharpe_ratio'),
                    'volatility': result.get('volatility'),
                    'win_rate': result.get('win_rate'),
                    'profit_factor': result.get('profit_factor')
                }
                existing_status.logs = result.get('logs', [])
                existing_status.status = 'completed'
                existing_status.updated_at = datetime.now()
                existing_status.completed_at = datetime.now()
                
                status_record = existing_status
                operation_type = 'update'
            else:
                # 创建新的状态记录
                status_record = BacktestStatus(
                    name=backtest_name,
                    description=backtest_description or f"回测: {symbol} ({start_date} 至 {end_date})",
                    strategy_id=strategy.id if strategy else None,
                    strategy_snapshot_id=strategy_snapshot.id if strategy_snapshot else None,
                    start_date=datetime.fromisoformat(start_date.replace('Z', '+00:00')),
                    end_date=datetime.fromisoformat(end_date.replace('Z', '+00:00')),
                    initial_capital=initial_capital,
                    instruments=[symbol],
                    # 保存完整的参数信息，包括策略参数
                    parameters=self._prepare_full_parameters(parameters),
                    position_config=parameters.get('positionConfig'),
                    # 保存回测结果数据
                    results=result,
                    equity_curve=result.get('equity_curve'),
                    trade_records=result.get('trades'),  # 回测引擎返回的字段名是'trades'
                    performance_metrics={
                        'total_return': result.get('total_return'),
                        'annual_return': result.get('annual_return'),  # 添加年化收益率
                        'max_drawdown': result.get('max_drawdown'),
                        'sharpe_ratio': result.get('sharpe_ratio'),
                        'volatility': result.get('volatility'),
                        'win_rate': result.get('win_rate'),
                        'profit_factor': result.get('profit_factor')
                    },
                    logs=result.get('logs', []),
                    status='completed',
                    completed_at=datetime.now()
                )
                self.db.add(status_record)
                self.db.flush()  # 获取ID
                operation_type = 'create'
            
            # 5. 创建历史记录
            history_record = BacktestHistory(
                status_id=status_record.id,
                start_date=status_record.start_date,
                end_date=status_record.end_date,
                initial_capital=status_record.initial_capital,
                instruments=status_record.instruments,
                parameters=status_record.parameters,
                position_config=status_record.position_config,
                # 保存回测结果数据到历史记录
                results=status_record.results,
                equity_curve=status_record.equity_curve,
                trade_records=status_record.trade_records,
                performance_metrics=status_record.performance_metrics,
                logs=status_record.logs,
                status=status_record.status,
                completed_at=status_record.completed_at,
                operation_type=operation_type
            )
            self.db.add(history_record)
            
            # 6. 同时保留旧架构的兼容性（可选）
            # 创建旧架构的回测记录以保持向后兼容
            backtest = Backtest(
                name=backtest_name,
                description=backtest_description or f"回测: {symbol} ({start_date} 至 {end_date})",
                strategy_id=strategy.id if strategy else None,
                strategy_snapshot_id=strategy_snapshot.id if strategy_snapshot else None,
                start_date=status_record.start_date,
                end_date=status_record.end_date,
                initial_capital=initial_capital,
                instruments=[symbol],
                parameters=parameters,
                position_config=parameters.get('positionConfig'),
                # 保存回测结果数据到旧架构记录
                results=result,
                equity_curve=result.get('equity_curve'),
                trade_records=result.get('trades'),  # 回测引擎返回的字段名是'trades'
                performance_metrics={
                    'total_return': result.get('total_return'),
                    'annual_return': result.get('annual_return'),  # 添加年化收益率
                    'max_drawdown': result.get('max_drawdown'),
                    'sharpe_ratio': result.get('sharpe_ratio'),
                    'volatility': result.get('volatility'),
                    'win_rate': result.get('win_rate'),
                    'profit_factor': result.get('profit_factor')
                },
                status='completed',
                completed_at=datetime.now()
            )
            self.db.add(backtest)
            
            self.db.commit()
            self.db.refresh(status_record)
            self.db.refresh(history_record)
            self.db.refresh(backtest)
            
            logger.info(f"回测结果已保存到新架构: 状态ID={status_record.id}, 历史ID={history_record.id}, 旧记录ID={backtest.id}")
            
        except Exception as e:
            logger.error(f"保存回测结果失败: {e}")
            self.db.rollback()
            raise