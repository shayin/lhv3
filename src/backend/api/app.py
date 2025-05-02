from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import os
import sys
import json
from sqlalchemy import text

# 添加系统路径，确保可以导入后端模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..models import get_db, init_db
from ..data import DataFetcher, DataProcessor
from ..strategy.templates import MovingAverageCrossover, BollingerBandsStrategy, MACDStrategy, RSIStrategy
from ..backtest import BacktestEngine, PerformanceAnalyzer
from ..config import FRONTEND_URL
from . import data_routes

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="量化交易回测系统API",
    description="提供数据管理、策略回测和分析的API接口",
    version="0.1.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，方便调试
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"收到请求: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"请求处理完成: {request.method} {request.url.path} - 状态码: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"请求处理错误: {request.method} {request.url.path} - 错误: {str(e)}")
        raise

# 注册数据管理路由
app.include_router(data_routes.router, prefix="/api/data", tags=["数据管理"])

# 初始化数据库
@app.on_event("startup")
async def startup():
    try:
        # 确保每次启动时初始化数据库表结构
        init_db()
        logger.info("数据库初始化成功，所有表已创建")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

# 健康检查端点
@app.get("/")
async def root():
    return {"status": "success", "message": "量化交易回测系统API服务已启动"}

@app.get("/health")
async def health_check():
    return {"status": "success", "service": "API Server", "version": "0.1.0"}

# 数据API
@app.get("/api/data/symbols")
async def get_symbols(db: Session = Depends(get_db)):
    """获取支持的股票列表"""
    try:
        # 这里可以从数据库中获取股票列表
        # 示例数据
        symbols = [
            {"symbol": "AAPL", "name": "苹果公司", "exchange": "纳斯达克"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "纳斯达克"},
            {"symbol": "MSFT", "name": "微软公司", "exchange": "纳斯达克"},
            {"symbol": "AMZN", "name": "亚马逊公司", "exchange": "纳斯达克"},
            {"symbol": "600000.SS", "name": "浦发银行", "exchange": "上证"},
            {"symbol": "000001.SZ", "name": "平安银行", "exchange": "深证"},
        ]
        return {"status": "success", "data": symbols}
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/fetch")
async def fetch_data(
    symbol: str = Query(..., description="股票代码"),
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    data_source: str = Query("yahoo", description="数据源 (yahoo, akshare)"),
    features: Optional[List[str]] = Query(None, description="要添加的技术指标，如 sma, macd, rsi 等")
):
    """获取股票历史数据并添加技术指标"""
    try:
        # 创建数据获取器和处理器
        fetcher = DataFetcher()
        processor = DataProcessor()
        
        # 获取原始数据
        data = fetcher.fetch_data(symbol, start_date, end_date, data_source)
        
        # 处理数据和添加特征
        if features:
            data = processor.process_data(data, features)
            
        # 转换为JSON兼容格式
        if not data.empty:
            data['date'] = data['date'].dt.strftime('%Y-%m-%d')
            
        result = data.to_dict(orient='records')
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"获取数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 策略API
@app.get("/api/strategies")
async def get_strategies(name: Optional[str] = None, include_templates: bool = True, db: Session = Depends(get_db)):
    """获取所有策略列表或按名称搜索"""
    try:
        logger.info(f"获取策略列表请求: 名称过滤={name}, 包含模板={include_templates}")
        
        # 导入策略模型
        from ..models.strategy import Strategy as StrategyModel
        
        # 构建查询
        query = db.query(StrategyModel)
        
        # 如果提供了名称参数，进行过滤
        if name:
            query = query.filter(StrategyModel.name.like(f"%{name}%"))
            logger.info(f"应用名称过滤条件: %{name}%")
        
        # 执行查询
        strategies = query.all()
        logger.info(f"找到 {len(strategies)} 个策略")
        
        # 处理结果并返回
        result_data = []
        for strategy in strategies:
            # 解析参数字符串为字典
            params_dict = {}
            if strategy.parameters:
                try:
                    params_dict = json.loads(strategy.parameters)
                except Exception as e:
                    logger.error(f"解析策略 {strategy.id} 的参数失败: {e}")
            
            # 构建单个策略数据
            strategy_data = {
                "id": strategy.id,
                "name": strategy.name,
                "description": strategy.description,
                "parameters": params_dict,
                "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
                "is_template": strategy.is_template,
                "template": strategy.template
            }
            result_data.append(strategy_data)
        
        # 如果需要包含预定义模板
        if include_templates:
            # 预定义策略模板
            predefined_strategies = [
                {
                    "id": "ma_crossover",
                    "name": "移动平均交叉策略",
                    "description": "利用短期和长期移动平均线交叉产生买卖信号",
                    "parameters": {
                        "short_window": {"type": "int", "default": 5, "min": 1, "max": 30, "description": "短期移动平均窗口"},
                        "long_window": {"type": "int", "default": 20, "min": 5, "max": 120, "description": "长期移动平均窗口"},
                    },
                    "is_template": True
                },
                {
                    "id": "bollinger_bands",
                    "name": "布林带策略",
                    "description": "利用价格突破布林带上下轨产生买卖信号",
                    "parameters": {
                        "window": {"type": "int", "default": 20, "min": 5, "max": 100, "description": "布林带窗口"},
                        "num_std": {"type": "float", "default": 2.0, "min": 0.5, "max": 4.0, "description": "标准差倍数"},
                    },
                    "is_template": True
                },
                {
                    "id": "macd",
                    "name": "MACD策略",
                    "description": "利用MACD指标的金叉和死叉产生买卖信号",
                    "parameters": {
                        "fast_period": {"type": "int", "default": 12, "min": 5, "max": 50, "description": "快速EMA周期"},
                        "slow_period": {"type": "int", "default": 26, "min": 10, "max": 100, "description": "慢速EMA周期"},
                        "signal_period": {"type": "int", "default": 9, "min": 3, "max": 30, "description": "信号线周期"},
                    },
                    "is_template": True
                },
                {
                    "id": "rsi",
                    "name": "RSI策略",
                    "description": "利用相对强弱指数的超买超卖产生买卖信号",
                    "parameters": {
                        "rsi_period": {"type": "int", "default": 14, "min": 5, "max": 50, "description": "RSI周期"},
                        "overbought": {"type": "int", "default": 70, "min": 60, "max": 90, "description": "超买阈值"},
                        "oversold": {"type": "int", "default": 30, "min": 10, "max": 40, "description": "超卖阈值"},
                    },
                    "is_template": True
                }
            ]
            
            # 如果有名称过滤条件，筛选预定义模板
            if name:
                predefined_strategies = [
                    s for s in predefined_strategies 
                    if name.lower() in s["name"].lower() or name.lower() in s["description"].lower()
                ]
            
            # 合并结果
            result_data.extend(predefined_strategies)
            logger.info(f"添加了 {len(predefined_strategies)} 个预定义策略模板")
        
        logger.info(f"最终返回 {len(result_data)} 个策略数据")
        
        return {
            "status": "success",
            "data": result_data
        }
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略列表失败: {str(e)}")

@app.post("/api/strategies")
async def create_strategy_endpoint(request: Request):
    try:
        data = await request.json()
        strategy = create_strategy(data)
        return strategy
    except Exception as e:
        logger.exception(f"创建策略端点错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建策略失败: {str(e)}")

def create_strategy(data):
    """创建新策略"""
    try:
        logger.info(f"处理策略创建请求: {data}")
        
        from ..models.strategy import Strategy as StrategyModel
        from sqlalchemy import text
        
        # 获取SQLAlchemy数据库会话
        db = next(get_db())
        
        name = data.get("name")
        
        if not name:
            logger.error("请求中没有策略名称")
            raise HTTPException(status_code=400, detail="缺少策略名称")
        
        # 检查是否存在具有相同名称的策略
        check_sql = f"SELECT * FROM strategies WHERE name = '{name}'"
        logger.info(f"执行SQL查询: {check_sql}")
        
        existing = db.query(StrategyModel).filter(StrategyModel.name == name).first()
        
        # 处理参数字段
        parameters = data.get("parameters")
        template_type = data.get("template")  # 获取模板类型
        
        if parameters is not None:
            if isinstance(parameters, dict):
                parameters = json.dumps(parameters)
                logger.info(f"已将参数字典序列化为JSON字符串: {parameters}")
            elif isinstance(parameters, str):
                # 验证是否为有效的JSON字符串
                try:
                    json.loads(parameters)
                    logger.info("参数已经是有效的JSON字符串")
                except Exception as e:
                    logger.error(f"提供的参数字符串不是有效的JSON: {e}")
                    raise HTTPException(status_code=400, detail="提供的参数不是有效的JSON格式")
            else:
                logger.error(f"不支持的参数类型: {type(parameters)}")
                raise HTTPException(status_code=400, detail="不支持的参数类型")
        
        if existing:
            logger.info(f"存在同名策略，更新现有策略: {existing.name} (ID: {existing.id})")
            # 更新现有策略字段
            existing.description = data.get("description", existing.description)
            existing.code = data.get("code", existing.code)
            existing.parameters = parameters
            existing.template = template_type  # 更新模板类型
            existing.is_template = data.get("is_template", existing.is_template)
            existing.updated_at = datetime.now()
            
            # 使用现有策略
            strategy = existing
        else:
            # 实例化新策略模型
            strategy = StrategyModel(
                name=data.get("name"),
                description=data.get("description"),
                code=data.get("code"),
                parameters=parameters,  # 使用处理后的参数
                template=template_type,  # 使用模板类型
                is_template=data.get("is_template", False),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            # 添加到会话
            db.add(strategy)
        
        logger.info(f"创建的策略对象参数: parameters={strategy.parameters}, 类型={type(strategy.parameters)}")
        
        # 执行SQL语句检查，使用text()函数
        check_table_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='strategies'"
        logger.info(f"执行SQL查询: {check_table_sql}")
        table_check = db.execute(text(check_table_sql)).fetchone()
        logger.info(f"数据库表检查结果: {table_check}")
        
        if not table_check:
            logger.error("strategies表不存在!")
            raise HTTPException(status_code=500, detail="数据库表不存在")
            
        # 获取ID
        db.flush()  # 获取ID但不提交
        generated_id = strategy.id
        logger.info(f"生成新策略ID: {generated_id}")
        
        # 记录当前策略对象状态
        logger.info(f"策略对象状态: {strategy.__dict__}")
        
        # 提交到数据库
        db.commit()
        
        # 验证创建是否成功
        verification_sql = f"SELECT * FROM strategies WHERE id = {strategy.id}"
        logger.info(f"执行验证SQL: {verification_sql}")
        verification_result = db.execute(text(verification_sql)).fetchone()
        logger.info(f"验证结果: {verification_result}")
        
        # 使用原生SQL查询再次检查
        raw_check_sql = f"SELECT COUNT(*) FROM strategies WHERE id = {strategy.id}"
        logger.info(f"执行计数SQL: {raw_check_sql}")
        raw_check = db.execute(text(raw_check_sql)).scalar()
        logger.info(f"原生SQL验证结果: 找到{raw_check}条记录")
        
        # 使用ORM查询验证
        new_strategy = db.query(StrategyModel).get(strategy.id)
        if not new_strategy:
            logger.error(f"策略创建验证失败: 未找到ID为{strategy.id}的策略")
            raise HTTPException(status_code=500, detail="策略创建成功但无法验证")
        
        logger.info(f"ORM查询到的策略信息: {new_strategy.__dict__}")
        
        # 解析参数
        params_dict = {}
        if new_strategy.parameters:
            try:
                params_dict = json.loads(new_strategy.parameters)
                logger.info(f"成功解析参数: {params_dict}")
            except Exception as e:
                logger.error(f"解析参数失败: {e}")
                params_dict = {}
        
        # 返回创建的策略数据
        result_data = {
            "id": new_strategy.id,
            "name": new_strategy.name,
            "description": new_strategy.description,
            "parameters": params_dict,
            "created_at": new_strategy.created_at.isoformat() if new_strategy.created_at else None,
            "updated_at": new_strategy.updated_at.isoformat() if new_strategy.updated_at else None,
            "is_template": new_strategy.is_template,
            "template": new_strategy.template
        }
        
        logger.info(f"返回给客户端的数据: {result_data}")
        
        # 记录操作结果
        if existing:
            logger.info(f"成功更新策略: {strategy.name} (ID: {strategy.id})")
            operation_message = "策略更新成功"
        else:
            logger.info(f"成功创建策略: {strategy.name} (ID: {strategy.id})")
            operation_message = "策略创建成功"
        
        # 验证操作是否成功
        return {
            "status": "success",
            "message": operation_message,
            "data": result_data
        }
    except HTTPException as he:
        # 直接重新抛出HTTP异常
        raise he
    except Exception as e:
        logger.error(f"处理策略创建请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建策略时发生错误: {str(e)}")

@app.get("/api/strategies/{strategy_id}")
async def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    try:
        logger.info(f"获取策略请求: ID={strategy_id}")
        
        # 导入策略模型（如果尚未导入）
        from ..models.strategy import Strategy as StrategyModel
        
        # 构建SQL查询
        sql_query = f"SELECT * FROM strategies WHERE id = {strategy_id}"
        logger.info(f"执行SQL查询: {sql_query}")
        
        strategy = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
        if not strategy:
            logger.warning(f"未找到策略: ID={strategy_id}")
            raise HTTPException(status_code=404, detail=f"未找到ID为{strategy_id}的策略")
        
        logger.info(f"找到策略: {strategy.name} (ID: {strategy.id})")
        
        # 解析参数字符串为字典
        params_dict = {}
        if strategy.parameters:
            try:
                params_dict = json.loads(strategy.parameters)
                logger.info(f"成功解析参数: {params_dict}")
            except Exception as e:
                logger.error(f"解析参数失败: {e}")
                params_dict = {}
        
        # 构建返回数据
        result_data = {
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "code": strategy.code,
            "parameters": params_dict,
            "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
            "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
            "is_template": strategy.is_template,
            "template": strategy.template  # 添加模板字段
        }
        
        logger.info(f"返回策略数据: ID={strategy.id}, 名称={strategy.name}")
        
        return {
            "status": "success",
            "data": result_data
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取策略时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取策略时发生错误: {str(e)}")

@app.put("/api/strategies/{strategy_id}")
async def update_strategy(strategy_id: int, request: Request, db: Session = Depends(get_db)):
    """更新现有策略"""
    try:
        data = await request.json()
        logger.info(f"更新策略请求: ID={strategy_id}, 数据={data}")
        
        # 从数据库获取策略
        from ..models.strategy import Strategy as StrategyModel
        
        # 构建SQL查询
        sql_query = f"SELECT * FROM strategies WHERE id = {strategy_id}"
        logger.info(f"执行SQL查询: {sql_query}")
        
        db_strategy = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
        
        if not db_strategy:
            logger.warning(f"未找到要更新的策略: ID={strategy_id}")
            raise HTTPException(status_code=404, detail=f"找不到ID为{strategy_id}的策略")
        
        logger.info(f"找到要更新的策略: {db_strategy.name} (ID: {db_strategy.id})")
        
        # 处理参数字段
        if "parameters" in data:
            parameters = data["parameters"]
            if parameters is not None:
                if isinstance(parameters, dict):
                    parameters = json.dumps(parameters)
                    logger.info(f"已将参数字典序列化为JSON字符串: {parameters}")
                elif isinstance(parameters, str):
                    # 验证是否为有效的JSON字符串
                    try:
                        json.loads(parameters)
                        logger.info("参数已经是有效的JSON字符串")
                    except Exception as e:
                        logger.error(f"提供的参数字符串不是有效的JSON: {e}")
                        raise HTTPException(status_code=400, detail="提供的参数不是有效的JSON格式")
                else:
                    logger.error(f"不支持的参数类型: {type(parameters)}")
                    raise HTTPException(status_code=400, detail="不支持的参数类型")
                
                data["parameters"] = parameters
        
        # 更新策略字段
        if "name" in data:
            db_strategy.name = data["name"]
        if "description" in data:
            db_strategy.description = data["description"]
        if "code" in data:
            db_strategy.code = data["code"]
        if "parameters" in data:
            db_strategy.parameters = data["parameters"]
        if "is_template" in data:
            db_strategy.is_template = data["is_template"]
        if "template" in data:
            db_strategy.template = data["template"]
        
        db_strategy.updated_at = datetime.now()
        
        # 记录更新状态
        logger.info(f"更新后的策略对象: {db_strategy.__dict__}")
        
        # 保存到数据库
        update_query = f"UPDATE strategies SET name='{db_strategy.name}', description='{db_strategy.description or ''}', template='{db_strategy.template or ''}', parameters='{db_strategy.parameters or ''}' WHERE id={strategy_id}"
        logger.info(f"执行更新SQL: {update_query}")
        
        db.commit()
        logger.info(f"策略更新成功: ID={db_strategy.id}, 名称={db_strategy.name}")
        
        # 解析参数字符串为字典
        params_dict = {}
        if db_strategy.parameters:
            try:
                params_dict = json.loads(db_strategy.parameters)
                logger.info(f"成功解析参数: {params_dict}")
            except Exception as e:
                logger.error(f"解析参数失败: {e}")
                params_dict = {}
        
        # 返回更新后的策略
        result_data = {
            "id": db_strategy.id,
            "name": db_strategy.name,
            "description": db_strategy.description,
            "code": db_strategy.code,
            "parameters": params_dict,
            "created_at": db_strategy.created_at.isoformat() if db_strategy.created_at else None,
            "updated_at": db_strategy.updated_at.isoformat() if db_strategy.updated_at else None,
            "is_template": db_strategy.is_template,
            "template": db_strategy.template
        }
        
        return {
            "status": "success",
            "message": "策略更新成功",
            "data": result_data
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"更新策略时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新策略时发生错误: {str(e)}")

@app.delete("/api/strategies/{strategy_id}")
async def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """删除策略"""
    try:
        # 从数据库获取策略
        from ..models.strategy import Strategy as StrategyModel
        db_strategy = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
        
        if not db_strategy:
            raise HTTPException(status_code=404, detail=f"找不到ID为{strategy_id}的策略")
        
        # 删除策略
        db.delete(db_strategy)
        db.commit()
        
        logger.info(f"删除策略成功: {db_strategy.name}(ID: {strategy_id})")
        
        return {"status": "success", "message": "策略删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除策略失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategies/test")
async def test_strategy(
    data: Dict[str, Any]
):
    """测试交易策略"""
    try:
        # 获取请求参数
        strategy_id = data.get("strategy_id")
        symbol = data.get("symbol")
        start_date = data.get("start_date")
        end_date = data.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        initial_capital = float(data.get("initial_capital", 100000))
        parameters = data.get("parameters", {})
        data_source = data.get("data_source", "yahoo")
        features = data.get("features", [])
        
        logger.info("=" * 80)
        logger.info(f"开始策略回测 - 股票: {symbol}, 策略: {strategy_id}")
        logger.info(f"回测参数: 日期范围={start_date}至{end_date}, 初始资金={initial_capital}, 数据源={data_source}")
        logger.info(f"策略参数: {parameters}")
        logger.info(f"特征列表: {features}")
        logger.info("-" * 80)
        
        # 数据源名称到ID的映射
        data_source_map = {
            "yahoo finance": "yahoo",
            "yahoo": "yahoo",
            "a股数据": "akshare", 
            "akshare": "akshare",
            "用户上传": "local",
            "local": "local"
        }
        
        # 如果传入的是数据源名称，转换为对应的数据源ID
        if isinstance(data_source, str) and data_source.lower() in data_source_map:
            data_source = data_source_map[data_source.lower()]
        
        # 参数检查
        if not strategy_id:
            raise ValueError("未提供策略ID")
        if not symbol:
            raise ValueError("未提供股票代码")
        if not start_date:
            raise ValueError("未提供开始日期")
        
        logger.info(f"开始回测策略: {strategy_id}, 交易品种: {symbol}, 日期范围: {start_date} 至 {end_date}, 数据源: {data_source}")
        
        # 1. 获取数据
        fetcher = DataFetcher()
        processor = DataProcessor()
        
        # 获取原始数据
        raw_data = fetcher.fetch_data(symbol, start_date, end_date, data_source)
        if raw_data is None or raw_data.empty:
            raise ValueError(f"无法获取{symbol}的数据，请检查股票代码是否正确或数据源{data_source}是否支持该股票")
        
        logger.info(f"获取到原始数据，行数: {len(raw_data)}")
        
        # 检查数据日期范围，如果超出范围则调整
        if 'date' in raw_data.columns:
            actual_start_date = raw_data['date'].min()
            actual_end_date = raw_data['date'].max()
            original_start_date = pd.to_datetime(start_date)
            original_end_date = pd.to_datetime(end_date)
            
            # 检查原始日期范围是否完全在数据范围外
            completely_outside = (original_start_date > actual_end_date) or (original_end_date < actual_start_date)
            
            if original_start_date < actual_start_date or original_end_date > actual_end_date or completely_outside:
                # 如果日期范围完全在数据范围外，则使用数据的完整范围
                if completely_outside:
                    adjusted_start_date = actual_start_date
                    adjusted_end_date = actual_end_date
                else:
                    adjusted_start_date = max(original_start_date, actual_start_date)
                    adjusted_end_date = min(original_end_date, actual_end_date)
                
                logger.warning(
                    f"调整回测日期范围: 原始范围 {start_date} 至 {end_date} 超出数据实际范围 "
                    f"{actual_start_date.strftime('%Y-%m-%d')} 至 {actual_end_date.strftime('%Y-%m-%d')}。"
                    f"已调整为: {adjusted_start_date.strftime('%Y-%m-%d')} 至 {adjusted_end_date.strftime('%Y-%m-%d')}"
                )
                
                # 更新日期范围
                start_date = adjusted_start_date.strftime("%Y-%m-%d")
                end_date = adjusted_end_date.strftime("%Y-%m-%d")
                
                # 根据调整后的日期范围过滤数据
                raw_data = raw_data[(raw_data['date'] >= adjusted_start_date) & (raw_data['date'] <= adjusted_end_date)]
                
                if raw_data.empty:
                    raise ValueError(f"调整日期范围后数据为空，无法进行回测。请检查数据是否覆盖了所需的时间区间。")
        
        # 处理数据和添加特征
        stock_data = processor.process_data(raw_data, features)
        if stock_data is None or stock_data.empty:
            raise ValueError(f"处理{symbol}的数据失败，请检查数据格式")
        
        logger.info(f"处理后的数据，行数: {len(stock_data)}")
        
        # 2. 加载策略
        strategy = None
        # 确保parameters是字典类型
        if not isinstance(parameters, dict):
            parameters = {}
            logger.warning(f"传入的parameters参数不是字典类型，已重置为空字典")
            
        if strategy_id == "ma_crossover":
            logger.info(f"使用策略: 移动平均线交叉策略，参数: {parameters}")
            strategy = MovingAverageCrossover(parameters=parameters)
        elif strategy_id == "bollinger_bands":
            logger.info(f"使用策略: 布林带策略，参数: {parameters}")
            strategy = BollingerBandsStrategy(parameters=parameters)
        elif strategy_id == "macd":
            logger.info(f"使用策略: MACD策略，参数: {parameters}")
            strategy = MACDStrategy(parameters=parameters)
        elif strategy_id == "rsi":
            logger.info(f"使用策略: RSI策略，参数: {parameters}")
            strategy = RSIStrategy(parameters=parameters)
        else:
            raise ValueError(f"不支持的策略ID: {strategy_id}")
        
        # 设置策略的数据
        strategy.set_data(stock_data)
            
        # 3. 生成交易信号
        logger.info("生成交易信号")
        signals = strategy.generate_signals()
        if signals is None or signals.empty:
            raise ValueError("生成交易信号失败")
        
        # 4. 回测策略
        logger.info("执行策略回测")
        # 执行回测，直接传入初始资金
        backtest_results = strategy.backtest(initial_capital=initial_capital)
        
        # 5. 如果回测结果显示有错误，则返回错误信息
        if backtest_results is None:
            logger.error("回测返回空结果")
            raise ValueError("回测失败，未返回结果")
        if 'error' in backtest_results:
            logger.error(f"回测返回错误: {backtest_results['error']}")
            raise ValueError(f"回测失败: {backtest_results['error']}")
        
        # 6. 组合结果
        trades = backtest_results.get('trades', [])
        
        # 日志输出交易统计摘要
        if trades:
            buy_trades = sum(1 for trade in trades if trade.get('action') == 'BUY')
            sell_trades = sum(1 for trade in trades if trade.get('action') == 'SELL')
            win_trades = sum(1 for trade in trades if trade.get('action') == 'SELL' and trade.get('profit', 0) > 0)
            loss_trades = sum(1 for trade in trades if trade.get('action') == 'SELL' and trade.get('profit', 0) < 0)
            total_profit = sum(trade.get('profit', 0) for trade in trades if trade.get('action') == 'SELL' and trade.get('profit', 0) > 0)
            total_loss = sum(trade.get('profit', 0) for trade in trades if trade.get('action') == 'SELL' and trade.get('profit', 0) < 0)
            
            logger.info("交易统计摘要:")
            logger.info(f"总交易次数: {len(trades)}, 买入: {buy_trades}, 卖出: {sell_trades}")
            logger.info(f"盈利交易: {win_trades}, 亏损交易: {loss_trades}")
            logger.info(f"总盈利: {total_profit:.2f}, 总亏损: {total_loss:.2f}, 净盈亏: {total_profit + total_loss:.2f}")
            
            if loss_trades > 0 and total_loss != 0:
                avg_win = total_profit / win_trades if win_trades > 0 else 0
                avg_loss = total_loss / loss_trades
                profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
                logger.info(f"平均盈利: {avg_win:.2f}, 平均亏损: {avg_loss:.2f}, 盈亏比: {profit_factor:.2f}")
        else:
            logger.info("无交易记录")
        
        # 为了兼容性，处理不同的回测结果格式
        performance = {}
        if 'performance' in backtest_results:
            performance = backtest_results['performance']
        else:
            # 从基本结果中提取性能指标
            performance = {
                'total_return': backtest_results.get('total_return', 0),
                'annual_return': backtest_results.get('annual_return', 0),
                'sharpe_ratio': backtest_results.get('sharpe', 0),
                'max_drawdown': backtest_results.get('max_drawdown', 0),
                'win_rate': backtest_results.get('win_rate', 0)
            }
        
        equity_curve = backtest_results.get('equity_curve', [])
        if not equity_curve and 'returns' in backtest_results:
            # 从returns提取权益曲线数据
            returns_data = backtest_results.get('returns', {})
            if returns_data and 'date' in returns_data and 'cum_returns' in returns_data:
                equity_curve = [
                    {'date': date, 'equity': cum_return * initial_capital}
                    for date, cum_return in zip(returns_data['date'], returns_data['cum_returns'])
                ]
        
        drawdowns = backtest_results.get('drawdowns', [])
        signals_data = backtest_results.get('signals', [])
        
        logger.info(f"回测完成, 总收益率: {performance.get('total_return', 0):.2f}%, 年化收益率: {performance.get('annual_return', 0):.2f}%")
        logger.info("=" * 80)
        
        # 构建结果对象
        result = {
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "symbol": symbol,
            "period": f"{start_date} 至 {end_date}",  # 使用调整后的日期范围
            "initial_capital": initial_capital,
            "final_capital": initial_capital * (1 + (performance.get('total_return', 0) / 100)),
            "total_return": performance.get('total_return', 0),
            "annual_return": performance.get('annual_return', 0),
            "sharpe_ratio": performance.get('sharpe_ratio', 0) or performance.get('sharpe', 0),
            "max_drawdown": performance.get('max_drawdown', 0),
            "win_rate": performance.get('win_rate', 0),
            "parameters": parameters,
            "trades_count": len(trades),
            # 转换交易记录为JSON兼容格式
            "trades": trades,
            "signals": signals_data
        }
        
        # 添加权益曲线数据
        if equity_curve:
            result["equity_curve"] = equity_curve
            
        # 添加回撤数据
        if drawdowns:
            result["drawdowns"] = drawdowns
        
        return {"status": "success", "data": result}
    except Exception as e:
        import traceback
        stack_trace = traceback.format_exc()
        logger.error(f"策略测试失败: {e}\n堆栈跟踪: {stack_trace}")
        return {"status": "error", "detail": str(e), "stack_trace": stack_trace}

# 回测API
@app.post("/api/backtest/optimize")
async def optimize_strategy(
    data: Dict[str, Any]
):
    """优化策略参数"""
    try:
        # 获取请求参数
        strategy_id = data.get("strategy_id")
        symbol = data.get("symbol")
        start_date = data.get("start_date")
        end_date = data.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        initial_capital = float(data.get("initial_capital", 100000))
        parameter_ranges = data.get("parameter_ranges", {})
        data_source = data.get("data_source", "yahoo")
        features = data.get("features", [])
        
        # 参数检查
        if not strategy_id:
            raise ValueError("未提供策略ID")
        if not symbol:
            raise ValueError("未提供股票代码")
        if not start_date:
            raise ValueError("未提供开始日期")
        if not parameter_ranges:
            raise ValueError("未提供参数范围")
            
        # 1. 获取数据
        fetcher = DataFetcher()
        processor = DataProcessor()
        
        # 获取原始数据
        raw_data = fetcher.fetch_data(symbol, start_date, end_date, data_source)
        if raw_data is None or raw_data.empty:
            raise ValueError(f"无法获取{symbol}的数据，请检查股票代码是否正确或数据源{data_source}是否支持该股票")
            
        logger.info(f"获取到原始数据，行数: {len(raw_data)}")
        
        # 检查数据日期范围，如果超出范围则调整
        if 'date' in raw_data.columns:
            actual_start_date = raw_data['date'].min()
            actual_end_date = raw_data['date'].max()
            original_start_date = pd.to_datetime(start_date)
            original_end_date = pd.to_datetime(end_date)
            
            # 检查原始日期范围是否完全在数据范围外
            completely_outside = (original_start_date > actual_end_date) or (original_end_date < actual_start_date)
            
            if original_start_date < actual_start_date or original_end_date > actual_end_date or completely_outside:
                # 如果日期范围完全在数据范围外，则使用数据的完整范围
                if completely_outside:
                    adjusted_start_date = actual_start_date
                    adjusted_end_date = actual_end_date
                else:
                    adjusted_start_date = max(original_start_date, actual_start_date)
                    adjusted_end_date = min(original_end_date, actual_end_date)
                
                logger.warning(
                    f"调整参数优化日期范围: 原始范围 {start_date} 至 {end_date} 超出数据实际范围 "
                    f"{actual_start_date.strftime('%Y-%m-%d')} 至 {actual_end_date.strftime('%Y-%m-%d')}。"
                    f"已调整为: {adjusted_start_date.strftime('%Y-%m-%d')} 至 {adjusted_end_date.strftime('%Y-%m-%d')}"
                )
                
                # 更新日期范围
                start_date = adjusted_start_date.strftime("%Y-%m-%d")
                end_date = adjusted_end_date.strftime("%Y-%m-%d")
                
                # 根据调整后的日期范围过滤数据
                raw_data = raw_data[(raw_data['date'] >= adjusted_start_date) & (raw_data['date'] <= adjusted_end_date)]
                
                if raw_data.empty:
                    raise ValueError(f"调整日期范围后数据为空，无法进行参数优化。请检查数据是否覆盖了所需的时间区间。")
        
        # 处理数据和添加特征
        stock_data = processor.process_data(raw_data, features)
        if stock_data is None or stock_data.empty:
            raise ValueError(f"处理{symbol}的数据失败，请检查数据格式")
            
        logger.info(f"处理后的数据，行数: {len(stock_data)}")
        
        # 2. 生成参数组合
        parameter_sets = []
        
        # 检查参数范围格式
        for param_name, param_range in parameter_ranges.items():
            if 'values' not in param_range:
                raise ValueError(f"参数 {param_name} 的范围定义缺少 'values' 字段")
                
        # 递归生成参数组合
        def generate_param_sets(current_params, param_names, index):
            if index >= len(param_names):
                parameter_sets.append(current_params.copy())
                return
                
            param_name = param_names[index]
            param_range = parameter_ranges[param_name]
            
            for value in param_range['values']:
                current_params[param_name] = value
                generate_param_sets(current_params, param_names, index + 1)
                
        generate_param_sets({}, list(parameter_ranges.keys()), 0)
        
        # 3. 选择策略
        if strategy_id == "ma_crossover":
            strategy_class = MovingAverageCrossover
        elif strategy_id == "bollinger_bands":
            strategy_class = BollingerBandsStrategy
        elif strategy_id == "macd":
            strategy_class = MACDStrategy
        elif strategy_id == "rsi":
            strategy_class = RSIStrategy
        else:
            raise ValueError(f"不支持的策略ID: {strategy_id}")
            
        # 4. 创建回测引擎
        backtest_engine = BacktestEngine(
            data=stock_data,
            strategy=strategy_class(),
            initial_capital=initial_capital,
            start_date=start_date,
            end_date=end_date
        )
        
        # 5. 并行运行多组参数
        results = backtest_engine.run_parallel(parameter_sets)
        
        # 6. 分析结果
        analyzed_results = []
        for i, result in enumerate(results):
            analyzed_results.append({
                "parameters": result['parameters'],
                "total_return": result['performance'].get('total_return', 0),
                "annual_return": result['performance'].get('annual_return', 0),
                "sharpe_ratio": result['performance'].get('sharpe_ratio', 0),
                "max_drawdown": result['performance'].get('max_drawdown', 0),
                "win_rate": result['performance'].get('win_rate', 0),
                "trades_count": len(result['trades'])
            })
            
        # 7. 按照夏普比率排序
        analyzed_results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
        
        return {"status": "success", "data": analyzed_results}
    except Exception as e:
        logger.error(f"策略优化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 导出报告API
@app.post("/api/backtest/report")
async def generate_report(
    data: Dict[str, Any]
):
    """生成回测报告"""
    try:
        # 获取请求参数
        backtest_results = data.get("backtest_results")
        
        if not backtest_results:
            raise ValueError("未提供回测结果")
            
        # 分析回测结果
        analyzer = PerformanceAnalyzer(backtest_results)
        report_path = analyzer.generate_report()
        
        return {"status": "success", "data": {"report_path": report_path}}
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 