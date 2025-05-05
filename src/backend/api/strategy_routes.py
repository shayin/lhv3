from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import sys
import os
import importlib.util
import traceback

# 导入数据库模型
from ..models import get_db
from ..models.strategy import Strategy as StrategyModel
from ..utils.strategy_validator import StrategyValidator

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def get_strategies(
    name: Optional[str] = None, 
    include_templates: bool = True, 
    db: Session = Depends(get_db)
):
    """获取所有策略列表或按名称搜索"""
    try:
        logger.info(f"获取策略列表请求: 名称过滤={name}")
        
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
        
        return {"status": "success", "data": result_data}
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{strategy_id}")
async def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """获取策略详情"""
    try:
        logger.info(f"获取策略详情请求: ID={strategy_id}")
        
        # 查询策略
        strategy = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
        if not strategy:
            logger.warning(f"未找到策略: ID={strategy_id}")
            raise HTTPException(status_code=404, detail=f"未找到ID为{strategy_id}的策略")
        
        # 解析参数
        params_dict = {}
        if strategy.parameters:
            try:
                params_dict = json.loads(strategy.parameters)
            except Exception as e:
                logger.error(f"解析参数失败: {e}")
        
        # 构建响应数据
        result_data = {
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "code": strategy.code,  # 返回策略代码
            "parameters": params_dict,
            "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
            "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
            "is_template": strategy.is_template,
            "template": strategy.template
        }
        
        return {"status": "success", "data": result_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_strategy(request: Request, db: Session = Depends(get_db)):
    """创建新策略"""
    try:
        data = await request.json()
        logger.info(f"创建策略请求: {data}")
        
        # 校验必要字段
        name = data.get("name")
        code = data.get("code")
        
        if not name:
            raise HTTPException(status_code=400, detail="缺少必要字段: name")
        if not code:
            raise HTTPException(status_code=400, detail="缺少必要字段: code")
        
        # 验证策略代码
        is_valid, errors = StrategyValidator.validate_strategy_code(code)
        if not is_valid:
            error_message = "策略代码验证失败:\n" + "\n".join(errors)
            logger.warning(f"策略代码验证失败: {error_message}")
            raise HTTPException(status_code=400, detail=error_message)
        
        # 处理参数字段
        parameters = data.get("parameters")
        parameters_json = None
        
        if parameters is not None:
            if isinstance(parameters, dict):
                parameters_json = json.dumps(parameters)
            elif isinstance(parameters, str):
                try:
                    # 验证是有效的JSON字符串
                    json.loads(parameters)
                    parameters_json = parameters
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"参数不是有效的JSON格式: {e}")
            else:
                raise HTTPException(status_code=400, detail=f"不支持的参数类型: {type(parameters)}")
        
        # 检查是否存在同名策略
        existing = db.query(StrategyModel).filter(StrategyModel.name == name).first()
        
        if existing:
            # 更新已有策略
            existing.description = data.get("description", existing.description)
            existing.code = code
            existing.parameters = parameters_json
            existing.template = data.get("template", existing.template)
            existing.is_template = data.get("is_template", existing.is_template)
            existing.updated_at = datetime.now()
            
            strategy = existing
            db.flush()
            db.commit()
            
            logger.info(f"更新策略成功: {strategy.name} (ID: {strategy.id})")
            message = "策略更新成功"
        else:
            # 创建新策略
            strategy = StrategyModel(
                name=name,
                description=data.get("description"),
                code=code,
                parameters=parameters_json,
                template=data.get("template"),
                is_template=data.get("is_template", False),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.add(strategy)
            db.flush()
            db.commit()
            
            logger.info(f"创建策略成功: {strategy.name} (ID: {strategy.id})")
            message = "策略创建成功"
        
        # 解析参数为字典
        params_dict = {}
        if strategy.parameters:
            try:
                params_dict = json.loads(strategy.parameters)
            except Exception:
                params_dict = {}
        
        # 返回结果
        result_data = {
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "parameters": params_dict,
            "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
            "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
            "is_template": strategy.is_template,
            "template": strategy.template
        }
        
        return {
            "status": "success",
            "message": message,
            "data": result_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建策略失败: {e}")
        # 回滚数据库
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建策略失败: {str(e)}")

@router.put("/{strategy_id}")
async def update_strategy(strategy_id: int, request: Request, db: Session = Depends(get_db)):
    """更新策略"""
    try:
        data = await request.json()
        logger.info(f"更新策略请求: ID={strategy_id}, 数据={data}")
        
        # 查询策略
        strategy = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail=f"未找到ID为{strategy_id}的策略")
        
        # 如果提供了代码，验证代码有效性
        code = data.get("code")
        if code is not None:
            is_valid, errors = StrategyValidator.validate_strategy_code(code)
            if not is_valid:
                error_message = "策略代码验证失败:\n" + "\n".join(errors)
                logger.warning(f"策略代码验证失败: {error_message}")
                raise HTTPException(status_code=400, detail=error_message)
            
            # 更新代码
            strategy.code = code
        
        # 处理参数字段
        parameters = data.get("parameters")
        if parameters is not None:
            if isinstance(parameters, dict):
                strategy.parameters = json.dumps(parameters)
            elif isinstance(parameters, str):
                try:
                    # 验证是有效的JSON字符串
                    json.loads(parameters)
                    strategy.parameters = parameters
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"参数不是有效的JSON格式: {e}")
            else:
                raise HTTPException(status_code=400, detail=f"不支持的参数类型: {type(parameters)}")
        
        # 更新其他字段
        if "name" in data:
            strategy.name = data["name"]
        if "description" in data:
            strategy.description = data["description"]
        if "template" in data:
            strategy.template = data["template"]
        if "is_template" in data:
            strategy.is_template = data["is_template"]
        
        # 更新时间
        strategy.updated_at = datetime.now()
        
        # 提交更新
        db.commit()
        
        # 解析参数
        params_dict = {}
        if strategy.parameters:
            try:
                params_dict = json.loads(strategy.parameters)
            except Exception:
                params_dict = {}
        
        # 返回更新后的策略
        result_data = {
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "parameters": params_dict,
            "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
            "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
            "is_template": strategy.is_template,
            "template": strategy.template
        }
        
        logger.info(f"更新策略成功: {strategy.name} (ID: {strategy.id})")
        
        return {
            "status": "success",
            "message": "策略更新成功",
            "data": result_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新策略失败: {e}")
        # 回滚数据库
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新策略失败: {str(e)}")

@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """删除策略"""
    try:
        logger.info(f"删除策略请求: ID={strategy_id}")
        
        # 查询策略
        strategy = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail=f"未找到ID为{strategy_id}的策略")
        
        # 保存策略名称用于日志
        strategy_name = strategy.name
        
        # 删除策略
        db.delete(strategy)
        db.commit()
        
        logger.info(f"删除策略成功: {strategy_name} (ID: {strategy_id})")
        
        return {
            "status": "success",
            "message": f"策略'{strategy_name}'已成功删除"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除策略失败: {e}")
        # 回滚数据库
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除策略失败: {str(e)}")

@router.post("/test")
async def test_strategy(request: Request, db: Session = Depends(get_db)):
    """测试策略代码"""
    try:
        data = await request.json()
        code = data.get("code")
        test_data = data.get("data")
        parameters = data.get("parameters", {})
        strategy_id = data.get("strategy_id")
        
        logger.info(f"收到策略测试请求: strategy_id={strategy_id}, 参数={parameters}")
        
        # 如果提供了strategy_id，则从数据库获取策略代码
        if strategy_id and not code:
            logger.info(f"从数据库获取策略代码，策略ID: {strategy_id}")
            strategy = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
            if not strategy:
                error_msg = f"未找到ID为{strategy_id}的策略"
                logger.error(error_msg)
                raise HTTPException(status_code=404, detail=error_msg)
            code = strategy.code
            logger.info(f"成功获取策略代码，策略名称: {strategy.name}")
            
            # 如果没有提供参数，使用策略默认参数
            if not parameters and strategy.parameters:
                try:
                    parameters = json.loads(strategy.parameters)
                    logger.info(f"使用策略默认参数: {parameters}")
                except Exception as e:
                    logger.error(f"解析策略参数失败: {e}")
        
        if not code:
            error_msg = "缺少必要字段: code或strategy_id"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 验证策略代码
        logger.info("开始验证策略代码...")
        is_valid, errors = StrategyValidator.validate_strategy_code(code)
        if not is_valid:
            error_message = "策略代码验证失败:\n" + "\n".join(errors)
            logger.error(f"策略代码验证失败: {error_message}")
            return {
                "status": "error",
                "message": error_message,
                "data": {
                    "is_valid": False,
                    "errors": errors
                }
            }
        
        logger.info("策略代码验证通过")
        
        # 如果提供了测试数据，进行简单回测
        if test_data:
            try:
                logger.info("开始加载策略实例...")
                # 导入与实例化策略
                strategy_instance = load_strategy_from_code(code, parameters)
                logger.info(f"策略实例加载成功: {type(strategy_instance).__name__}")
                
                # 准备数据
                if isinstance(test_data, list):
                    df = pd.DataFrame(test_data)
                else:
                    df = pd.DataFrame()
                
                if not df.empty:
                    logger.info(f"测试数据加载成功，数据量: {len(df)}行")
                    # 设置数据
                    strategy_instance.set_data(df)
                    
                    # 生成信号
                    logger.info("开始生成交易信号...")
                    signals = strategy_instance.generate_signals()
                    
                    # 统计信号
                    buy_count = (signals['signal'] == 1).sum()
                    sell_count = (signals['signal'] == -1).sum()
                    logger.info(f"信号生成完成: 买入信号 {buy_count}个, 卖出信号 {sell_count}个")
                    
                    result = {
                        "signals": signals.to_dict(orient='records'),
                        "statistics": {
                            "total_records": len(signals),
                            "buy_signals": int(buy_count),
                            "sell_signals": int(sell_count)
                        }
                    }
                else:
                    logger.error("测试数据为空")
                    result = {"error": "测试数据为空"}
            except Exception as e:
                logger.error(f"策略测试失败: {e}")
                traceback.print_exc()
                result = {"error": f"策略测试失败: {str(e)}"}
        else:
            # 仅验证代码是否有效
            result = {"is_valid": True}
        
        logger.info("策略测试完成")
        return {
            "status": "success",
            "message": "策略代码验证通过",
            "data": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试策略失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"测试策略失败: {str(e)}")

def load_strategy_from_code(code: str, parameters: Dict[str, Any] = None):
    """
    从代码字符串加载策略类并实例化
    
    Args:
        code: 策略代码字符串
        parameters: 策略参数
        
    Returns:
        策略实例
    """
    temp_module_name = f"temp_strategy_module_{hash(code) % 10000}"
    
    try:
        # 创建临时模块
        logger.debug(f"创建临时模块: {temp_module_name}")
        spec = importlib.util.spec_from_loader(temp_module_name, loader=None)
        module = importlib.util.module_from_spec(spec)
        sys.modules[temp_module_name] = module
        
        # 执行代码
        exec(code, module.__dict__)
        
        # 查找策略类
        strategy_class = None
        from ..strategy.templates.strategy_template import StrategyTemplate
        
        for name, obj in module.__dict__.items():
            if (isinstance(obj, type) and 
                obj is not StrategyTemplate and 
                issubclass(obj, StrategyTemplate)):
                strategy_class = obj
                logger.debug(f"找到策略类: {name}")
                break
        
        if strategy_class is None:
            error_msg = "未找到策略类"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 实例化策略类
        logger.debug(f"实例化策略类: {strategy_class.__name__}, 参数: {parameters}")
        strategy_instance = strategy_class(parameters=parameters)
        return strategy_instance
    
    finally:
        # 清理临时模块
        if temp_module_name in sys.modules:
            del sys.modules[temp_module_name] 