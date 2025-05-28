import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session

from ..models.market_data import Stock, DailyPrice
from ..models.data_models import Stock as StockModel, StockData
from ..data.fetcher import DataFetcher
from ..data.processor import DataProcessor
from ..backtest.engine import BacktestEngine
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
                    features: Optional[List[str]] = None) -> Dict[str, Any]:
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
        logger.info("=" * 80)
        logger.info(f"开始回测: 策略={strategy_id}, 品种={symbol}, 日期={start_date}至{end_date}")
        logger.info(f"参数: 初始资金={initial_capital}, 手续费率={commission_rate}, 滑点率={slippage_rate}")
        
        # 记录仓位配置信息
        position_config = parameters.get('positionConfig', {}) if parameters else {}
        if position_config:
            position_mode = position_config.get('mode', 'fixed')
            logger.info(f"仓位模式: {position_mode}")
            if position_mode == 'fixed':
                default_size = position_config.get('defaultSize', 1.0) * 100
                logger.info(f"固定仓位比例: {default_size:.2f}%")
            elif position_mode == 'dynamic':
                dynamic_max = position_config.get('dynamicMax', 1.0) * 100
                logger.info(f"动态仓位最大比例: {dynamic_max:.2f}%")
            elif position_mode == 'staged':
                sizes = [size * 100 for size in position_config.get('sizes', [])]
                logger.info(f"分批建仓比例: {', '.join([f'{size:.2f}%' for size in sizes])}")
        
        if parameters:
            logger.info(f"其他策略参数: {parameters}")
        logger.info("-" * 80)
        
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
        
        # 2. 实例化策略
        strategy = self._get_strategy_instance(strategy_id, stock_data, parameters)
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
        
        # 4. 运行回测
        try:
            result = engine.run(stock_data)
            logger.info(f"回测完成: 总收益率={result['total_return']:.2%}, 最大回撤={result['max_drawdown']:.2%}")
            
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
            
        # 如果是字符串策略ID，根据名称创建实例
        if isinstance(strategy_id, str):
            if strategy_id == "ma_crossover":
                logger.info(f"创建策略: 移动平均线交叉策略, 参数: {parameters}")
                return MovingAverageCrossover(parameters=parameters)
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
        
        # 如果是数字ID，从数据库中获取策略
        elif isinstance(strategy_id, int) and self.db is not None:
            try:
                from ..models.strategy import Strategy as StrategyModel
                from ..api.strategy_routes import load_strategy_from_code
                
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
                    
                    # 输出策略代码前几行进行调试
                    code_preview = "\n".join(db_strategy.code.split("\n")[:5])
                    logger.debug(f"策略代码预览:\n{code_preview}")
                    
                    # 从代码加载策略
                    strategy_instance = load_strategy_from_code(db_strategy.code, data, parameters, globals_dict)
                    return strategy_instance
                except ImportError as ie:
                    logger.error(f"导入策略模板模块失败: {str(ie)}")
                    import sys
                    logger.error(f"Python路径: {sys.path}")
                    return None
            except Exception as e:
                logger.error(f"加载数据库策略失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return None
        
        logger.error(f"无法创建策略实例: {strategy_id}")
        return None 