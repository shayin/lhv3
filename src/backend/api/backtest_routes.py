from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import logging
import json
from datetime import datetime

from ..models.base import get_db
from .backtest_service import BacktestService

router = APIRouter(prefix="/api/backtest", tags=["backtest"])
logger = logging.getLogger(__name__)

@router.post("/test")
async def test_backtest(request: Request, db: Session = Depends(get_db)):
    """运行策略回测"""
    try:
        data = await request.json()
        
        # 获取请求参数
        strategy_id = data.get("strategy_id")
        symbol = data.get("symbol")
        start_date = data.get("start_date")
        end_date = data.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        initial_capital = float(data.get("initial_capital", 100000))
        parameters = data.get("parameters", {})
        data_source = data.get("data_source", "database")  # 默认从数据库获取
        features = data.get("features", [])
        
        logger.info("=" * 80)
        logger.info(f"开始策略回测 - 股票: {symbol}, 策略: {strategy_id}")
        logger.info(f"回测参数: 日期范围={start_date}至{end_date}, 初始资金={initial_capital}, 数据源={data_source}")
        logger.info(f"策略参数: {parameters}")
        logger.info(f"特征列表: {features}")
        logger.info("-" * 80)
        
        # 参数检查
        if not strategy_id:
            raise ValueError("未提供策略ID")
        if not symbol:
            raise ValueError("未提供股票代码")
        if not start_date:
            raise ValueError("未提供开始日期")
        
        # 初始化回测服务
        backtest_service = BacktestService(db)
        
        # 运行回测
        result = backtest_service.run_backtest(
            strategy_id=strategy_id,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            parameters=parameters,
            data_source=data_source,
            features=features
        )
        
        return result
    
    except ValueError as ve:
        logger.error(f"参数错误: {str(ve)}")
        return {
            "status": "error",
            "message": str(ve),
            "data": None
        }
    except Exception as e:
        logger.error(f"测试策略失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"测试策略失败: {str(e)}",
            "data": None
        }

@router.post("/optimize")
async def optimize_strategy(request: Request, db: Session = Depends(get_db)):
    """优化策略参数"""
    try:
        data = await request.json()
        
        # 获取请求参数
        strategy_id = data.get("strategy_id")
        symbol = data.get("symbol")
        start_date = data.get("start_date")
        end_date = data.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        initial_capital = float(data.get("initial_capital", 100000))
        parameter_ranges = data.get("parameter_ranges", {})
        data_source = data.get("data_source", "database")
        
        logger.info("=" * 80)
        logger.info(f"开始策略参数优化 - 股票: {symbol}, 策略: {strategy_id}")
        logger.info(f"回测参数: 日期范围={start_date}至{end_date}, 初始资金={initial_capital}")
        logger.info(f"参数范围: {parameter_ranges}")
        logger.info("-" * 80)
        
        # 参数检查
        if not strategy_id:
            raise ValueError("未提供策略ID")
        if not symbol:
            raise ValueError("未提供股票代码")
        if not start_date:
            raise ValueError("未提供开始日期")
        if not parameter_ranges:
            raise ValueError("未提供参数优化范围")
        
        # 生成参数组合
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
        logger.info(f"生成了 {len(parameter_sets)} 组参数组合")
        
        # 初始化回测服务
        backtest_service = BacktestService(db)
        
        # 获取回测数据
        stock_data = backtest_service.get_backtest_data(
            symbol=symbol, 
            start_date=start_date, 
            end_date=end_date, 
            data_source=data_source
        )
        
        if stock_data.empty:
            raise ValueError(f"无法获取回测数据: {symbol}, {start_date}至{end_date}")
        
        # 运行多参数回测
        results = []
        for params in parameter_sets:
            logger.info(f"测试参数组合: {params}")
            try:
                result = backtest_service.run_backtest(
                    strategy_id=strategy_id,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    parameters=params,
                    data_source="memory"  # 使用已经获取的数据
                )
                
                if result["status"] == "success" and result["data"]:
                    # 提取结果数据
                    results.append({
                        "parameters": params,
                        "total_return": result["data"].get("total_return", 0),
                        "annual_return": result["data"].get("annual_return", 0),
                        "sharpe_ratio": result["data"].get("sharpe_ratio", 0),
                        "max_drawdown": result["data"].get("max_drawdown", 0),
                        "win_rate": result["data"].get("win_rate", 0),
                        "trades_count": len(result["data"].get("trades", []))
                    })
            except Exception as e:
                logger.error(f"参数组合 {params} 回测失败: {e}")
        
        # 按照夏普比率排序
        results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
        
        return {
            "status": "success",
            "message": f"优化完成，测试了{len(parameter_sets)}组参数",
            "data": results
        }
    
    except ValueError as ve:
        logger.error(f"参数错误: {str(ve)}")
        return {
            "status": "error",
            "message": str(ve),
            "data": None
        }
    except Exception as e:
        logger.error(f"策略优化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"策略优化失败: {str(e)}",
            "data": None
        }

@router.post("/report")
async def generate_report(request: Request, db: Session = Depends(get_db)):
    """生成回测报告"""
    try:
        data = await request.json()
        backtest_results = data.get("backtest_results")
        
        if not backtest_results:
            raise ValueError("未提供回测结果")
        
        # 这里应实现报告生成逻辑，可以调用PerformanceAnalyzer类
        # 或者直接返回回测结果，让前端进行展示
        
        # 示例实现
        from ..analysis.performance import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer(backtest_results)
        report_path = analyzer.generate_report()
        
        return {
            "status": "success",
            "message": "报告生成成功",
            "data": {"report_path": report_path}
        }
    
    except ValueError as ve:
        logger.error(f"参数错误: {str(ve)}")
        return {
            "status": "error",
            "message": str(ve),
            "data": None
        }
    except Exception as e:
        logger.error(f"生成报告失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"生成报告失败: {str(e)}",
            "data": None
        } 