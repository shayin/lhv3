from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Path, status, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
import pandas as pd
import logging
from datetime import datetime, timedelta
import shutil
import csv
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from ..models import get_db, Stock, DailyPrice, DataSource, StockData
from ..config import RAW_DATA_DIR, PROCESSED_DATA_DIR
from ..data import DataFetcher, DataProcessor

# 导入数据抓取模块
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.data_manager import DataManager

from uuid import uuid4
logger = logging.getLogger(__name__)
router = APIRouter()

# 确保数据目录存在
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

# 初始化数据管理器
data_manager = DataManager()
# 异步更新任务内存状态（简单实现，可后续迁移到数据库）
UPDATE_TASKS: Dict[str, Dict[str, Any]] = {}
# 一键更新任务状态存储
UPDATE_ALL_TASKS: Dict[str, Dict[str, Any]] = {}

def update_stock_statistics(db: Session, stock_id: int):
    """更新股票的统计信息（总记录数、开始日期、结束日期）"""
    try:
        # 查询股票的数据统计
        result = db.query(
            func.count(StockData.id).label('total_records'),
            func.min(StockData.date).label('first_date'),
            func.max(StockData.date).label('last_date')
        ).filter(StockData.stock_id == stock_id).first()
        
        # 更新股票记录
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if stock:
            stock.total_records = result.total_records or 0
            stock.first_date = result.first_date
            stock.last_date = result.last_date
            stock.last_updated = datetime.now()
            db.commit()
            
        return {
            'total_records': result.total_records or 0,
            'first_date': result.first_date,
            'last_date': result.last_date
        }
    except Exception as e:
        logger.error(f"更新股票统计信息失败: {str(e)}")
        db.rollback()
        raise

@router.get("/list", response_model=List[Dict[str, Any]])
async def list_data_sources(db: Session = Depends(get_db)):
    """获取所有数据源列表"""
    try:
        sources = db.query(DataSource).all()
        return [{"id": src.id, "name": src.name, "description": src.description} for src in sources]
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")

@router.get("/stocks", response_model=List[Dict[str, Any]])
async def list_stocks(
    type: Optional[str] = None,
    source_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取股票列表，可选按类型和数据源筛选"""
    try:
        query = db.query(Stock)
        
        if type:
            query = query.filter(Stock.type == type)
        if source_id:
            query = query.filter(Stock.source_id == source_id)
            
        stocks = query.all()
        
        result = []
        for stock in stocks:
            result.append({
                "id": stock.id,
                "symbol": stock.symbol,
                "name": stock.name,
                "type": stock.type,
                "source_id": stock.source_id,
                "last_updated": stock.last_updated.isoformat() if stock.last_updated else None,
                "data_count": stock.total_records or 0,
                "first_date": stock.first_date.strftime("%Y-%m-%d") if stock.first_date else None,
                "last_date": stock.last_date.strftime("%Y-%m-%d") if stock.last_date else None
            })
        
        return result
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")

@router.get("/stock/{stock_id}/date-range")
async def get_stock_date_range(
    stock_id: int = Path(..., description="股票ID"),
    db: Session = Depends(get_db)
):
    """获取股票的数据时间范围"""
    try:
        # 查找股票
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        return {
            "stock_id": stock_id,
            "symbol": stock.symbol,
            "name": stock.name,
            "data_count": stock.total_records or 0,
            "first_date": stock.first_date.strftime("%Y-%m-%d") if stock.first_date else None,
            "last_date": stock.last_date.strftime("%Y-%m-%d") if stock.last_date else None
        }
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")

@router.get("/stock/symbol/{symbol}/date-range")
async def get_stock_date_range_by_symbol(
    symbol: str = Path(..., description="股票代码"),
    db: Session = Depends(get_db)
):
    """通过股票代码获取股票的数据时间范围"""
    try:
        # 查找股票
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"股票代码 {symbol} 不存在")
        
        # 查找该股票的最早和最晚数据日期
        date_range = db.query(
            func.min(StockData.date).label('min_date'),
            func.max(StockData.date).label('max_date'),
            func.count(StockData.id).label('data_count')
        ).filter(StockData.stock_id == stock.id).first()
        
        if not date_range or not date_range.min_date:
            raise HTTPException(status_code=404, detail=f"股票代码 {symbol} 没有数据记录")
        
        return {
            "status": "success",
            "data": {
                "stock_id": stock.id,
                "symbol": stock.symbol,
                "name": stock.name,
                "min_date": date_range.min_date.strftime("%Y-%m-%d"),
                "max_date": date_range.max_date.strftime("%Y-%m-%d"),
                "data_count": date_range.data_count or 0
            }
        }
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")

@router.get("/stock/{stock_id}/last-date")
async def get_stock_last_date(
    stock_id: int = Path(..., description="股票ID"),
    db: Session = Depends(get_db)
):
    """获取股票的最后数据日期"""
    try:
        # 查找股票
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 查找该股票的最新数据日期
        latest_data = db.query(StockData).filter(
            StockData.stock_id == stock_id
        ).order_by(StockData.date.desc()).first()
        
        if not latest_data:
            raise HTTPException(status_code=404, detail="该股票没有数据记录")
        
        return {
            "stock_id": stock_id,
            "symbol": stock.symbol,
            "name": stock.name,
            "last_date": latest_data.date.strftime("%Y-%m-%d"),
            "last_updated": stock.last_updated.isoformat() if stock.last_updated else None
        }
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_stock_data(
    file: UploadFile = File(...),
    symbol: str = Query(..., description="股票代码"),
    name: str = Query(..., description="股票名称"),
    type: str = Query(..., description="股票类型: A股/港股/美股/期货/加密货币等"),
    source_id: int = Query(..., description="数据源ID"),
    db: Session = Depends(get_db)
):
    """上传股票CSV数据文件并导入到数据库"""
    # 检查数据源是否存在
    data_source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail=f"数据源ID {source_id} 不存在")

    # 检查文件格式
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="只支持CSV文件格式")
    
    # 保存上传的文件
    temp_file_path = os.path.join(RAW_DATA_DIR, f"temp_{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv")
    
    try:
        # 保存上传的文件
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 验证CSV文件格式
        try:
            df = pd.read_csv(temp_file_path)
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            
            # 检查必须的列是否存在
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise HTTPException(
                    status_code=400, 
                    detail=f"CSV文件缺少必需的列: {', '.join(missing_columns)}"
                )
                
            # 检查日期格式
            try:
                df['date'] = pd.to_datetime(df['date'])
            except Exception:
                raise HTTPException(status_code=400, detail="CSV文件中的日期格式无效")
                
            # 处理并导入数据
            processor = DataProcessor()
            processed_df = processor.process_data(df, features=[])
            
            # 检查股票是否已存在
            stock = db.query(Stock).filter(Stock.symbol == symbol).first()
            
            if not stock:
                # 创建新股票记录
                stock = Stock(
                    symbol=symbol,
                    name=name,
                    type=type,
                    source_id=source_id,
                    last_updated=datetime.now()
                )
                db.add(stock)
                db.commit()
                db.refresh(stock)
            else:
                # 更新现有股票
                stock.name = name
                stock.type = type
                stock.source_id = source_id
                stock.last_updated = datetime.now()
                db.commit()
            
            # 清除该股票的现有数据（可选，这里选择替换数据）
            db.query(StockData).filter(StockData.stock_id == stock.id).delete()
            
            # 导入新数据
            data_records = []
            for _, row in processed_df.iterrows():
                stock_data = StockData(
                    stock_id=stock.id,
                    date=row['date'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    adj_close=row.get('adj_close', row['close'])
                )
                data_records.append(stock_data)
            
            # 批量插入数据
            db.bulk_save_objects(data_records)
            db.commit()
            
            return {
                "status": "success",
                "message": f"成功导入{len(data_records)}条{symbol}的数据记录"
            }
                
        except pd.errors.EmptyDataError:
            raise HTTPException(status_code=400, detail="CSV文件为空")
        except pd.errors.ParserError:
            raise HTTPException(status_code=400, detail="CSV文件格式无效")
            
    except Exception as e:
        logger.error(f"处理上传文件时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理上传文件时发生错误: {str(e)}")
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

from pydantic import BaseModel

class FetchStockDataRequest(BaseModel):
    symbol: str
    name: str
    type: str
    source_id: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@router.post("/update/{stock_id}", status_code=status.HTTP_201_CREATED)
async def update_stock_data(
    stock_id: int = Path(..., description="股票ID"),
    db: Session = Depends(get_db)
):
    """更新股票数据，从最后日期抓取到今天"""
    try:
        # 查找股票
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 查找该股票的最新数据日期
        latest_data = db.query(StockData).filter(
            StockData.stock_id == stock_id
        ).order_by(StockData.date.desc()).first()
        
        if not latest_data:
            raise HTTPException(status_code=404, detail="该股票没有数据记录，请先抓取初始数据")
        
        # 计算开始日期（最后数据日期的下一天）
        last_date = latest_data.date
        start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        # 检查是否需要更新
        if start_date > end_date:
            return {
                "status": "success",
                "message": f"{stock.symbol} 数据已是最新，无需更新",
                "data": {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "last_date": last_date.strftime("%Y-%m-%d"),
                    "update_range": {
                        "start": start_date,
                        "end": end_date
                    }
                }
            }
        
        logger.info(f"开始更新股票数据: {stock.symbol} ({stock.name})")
        logger.info(f"更新日期范围: {start_date} 至 {end_date}")
        
        # 获取数据源信息
        data_source = db.query(DataSource).filter(DataSource.id == stock.source_id).first()
        if not data_source:
            raise HTTPException(status_code=404, detail=f"数据源ID {stock.source_id} 不存在")
        
        # 根据数据源名称确定使用哪个数据抓取器
        source_name = data_source.name.lower()
        
        if 'akshare' in source_name or '抓取' in source_name:
            # AkShare抓取数据源
            fetch_source = 'akshare'
        elif '用户上传' in source_name or 'user' in source_name:
            # 用户上传的数据，使用akshare抓取（因为目前只支持akshare）
            fetch_source = 'akshare'
        else:
            # 默认使用akshare
            fetch_source = 'akshare'
        
        logger.info(f"使用数据源: {fetch_source} 更新数据")
        
        # 检查数据源是否可用
        available_sources = data_manager.get_available_sources()
        if fetch_source not in available_sources:
            raise HTTPException(
                status_code=400, 
                detail=f"数据源 {fetch_source} 不可用，可用数据源: {', '.join(available_sources)}"
            )
        
        # 抓取数据
        file_path = data_manager.fetch_stock_data(fetch_source, stock.symbol, start_date, end_date)
        
        if not file_path:
            return {
                "status": "success",
                "message": f"{stock.symbol} 在指定日期范围内没有新数据（可能是周末或节假日）",
                "data": {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "last_date": last_date.strftime("%Y-%m-%d"),
                    "update_range": {
                        "start": start_date,
                        "end": end_date
                    },
                    "records_count": 0
                }
            }
        
        logger.info(f"数据抓取成功，文件路径: {file_path}")
        
        # 读取抓取的数据
        try:
            df = pd.read_csv(file_path)
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            
            # 检查必须的列是否存在
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise HTTPException(
                    status_code=400, 
                    detail=f"抓取的数据缺少必需的列: {', '.join(missing_columns)}"
                )
            
            # 检查数据是否为空
            if df.empty:
                return {
                    "status": "success",
                    "message": f"{stock.symbol} 在指定日期范围内没有新数据",
                    "data": {
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "last_date": last_date.strftime("%Y-%m-%d"),
                        "update_range": {
                            "start": start_date,
                            "end": end_date
                        },
                        "records_count": 0
                    }
                }
            
            # 检查日期格式
            try:
                df['date'] = pd.to_datetime(df['date'])
            except Exception:
                raise HTTPException(status_code=400, detail="抓取的数据中日期格式无效")
            
            # 处理数据
            processor = DataProcessor()
            processed_df = processor.process_data(df, features=[])
            
            # 导入新数据到数据库
            records_count = 0
            for _, row in processed_df.iterrows():
                # 检查是否已存在该日期的数据
                existing_data = db.query(StockData).filter(
                    StockData.stock_id == stock_id,
                    StockData.date == row['date']
                ).first()
                
                if not existing_data:
                    # 创建新数据记录
                    new_data = StockData(
                        stock_id=stock_id,
                        date=row['date'],
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume'],
                        adj_close=row.get('adj_close', row['close'])
                    )
                    db.add(new_data)
                    records_count += 1
            
            # 更新股票的最后更新时间和统计信息
            stock.last_updated = datetime.now()
            
            # 更新股票的统计信息（总记录数、开始日期、结束日期）
            if records_count > 0:
                # 查询最新的统计信息
                result = db.query(
                    func.count(StockData.id).label('total_records'),
                    func.min(StockData.date).label('first_date'),
                    func.max(StockData.date).label('last_date')
                ).filter(StockData.stock_id == stock_id).first()
                
                stock.total_records = result.total_records or 0
                stock.first_date = result.first_date
                stock.last_date = result.last_date
            
            db.commit()
            
            logger.info(f"成功更新 {records_count} 条 {stock.symbol} 的数据记录")
            
            return {
                "status": "success",
                "message": f"成功更新 {records_count} 条 {stock.symbol} 的数据记录",
                "data": {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "records_count": records_count,
                    "update_range": {
                        "start": start_date,
                        "end": end_date
                    },
                    "source": fetch_source
                }
            }
            
        except Exception as e:
            logger.error(f"处理抓取的数据时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=f"处理数据时出错: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新股票数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新股票数据失败: {str(e)}")

@router.post("/update/{stock_id}/async", status_code=status.HTTP_202_ACCEPTED)
async def update_stock_data_async(
    stock_id: int = Path(..., description="股票ID"),
):
    """异步更新股票数据：立即返回任务ID，后台线程执行更新，避免阻塞主事件循环"""
    task_id = str(uuid4())
    UPDATE_TASKS[task_id] = {
        "task_id": task_id,
        "stock_id": stock_id,
        "status": "queued",
        "message": "任务已提交"
    }
    # 使用后台线程执行，确保不阻塞当前请求处理
    import threading
    threading.Thread(target=_update_stock_data_runner, args=(task_id, stock_id), daemon=True).start()
    return {"status": "accepted", "task_id": task_id, "message": "更新任务已启动"}

@router.get("/update-tasks/{task_id}", status_code=status.HTTP_200_OK)
async def get_update_task_status(task_id: str = Path(..., description="任务ID")):
    """查询异步更新任务状态"""
    task = UPDATE_TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

from ..models.data_models import get_session

def _update_stock_data_runner(task_id: str, stock_id: int):
    """后台执行单股更新逻辑，并更新内存任务状态"""
    UPDATE_TASKS[task_id].update({"status": "running", "message": "正在更新"})
    db = get_session()
    try:
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not stock:
            UPDATE_TASKS[task_id].update({"status": "failed", "message": "股票不存在"})
            return
        latest_data = db.query(StockData).filter(StockData.stock_id == stock_id).order_by(StockData.date.desc()).first()
        if not latest_data:
            UPDATE_TASKS[task_id].update({"status": "failed", "message": "该股票没有数据记录，请先抓取初始数据"})
            return
        last_date = latest_data.date
        start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date > end_date:
            UPDATE_TASKS[task_id].update({
                "status": "completed",
                "message": f"{stock.symbol} 数据已是最新，无需更新",
                "data": {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "last_date": last_date.strftime("%Y-%m-%d"),
                    "update_range": {"start": start_date, "end": end_date}
                }
            })
            return
        data_source = db.query(DataSource).filter(DataSource.id == stock.source_id).first()
        if not data_source:
            UPDATE_TASKS[task_id].update({"status": "failed", "message": f"数据源ID {stock.source_id} 不存在"})
            return
        source_name = data_source.name.lower()
        if 'akshare' in source_name or '抓取' in source_name:
            fetch_source = 'akshare'
        elif '用户上传' in source_name or 'user' in source_name:
            fetch_source = 'akshare'
        else:
            fetch_source = 'akshare'
        available_sources = data_manager.get_available_sources()
        if fetch_source not in available_sources:
            UPDATE_TASKS[task_id].update({"status": "failed", "message": f"数据源 {fetch_source} 不可用"})
            return
        file_path = data_manager.fetch_stock_data(fetch_source, stock.symbol, start_date, end_date)
        if not file_path:
            UPDATE_TASKS[task_id].update({"status": "failed", "message": f"抓取股票 {stock.symbol} 数据失败"})
            return
        df = pd.read_csv(file_path)
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            UPDATE_TASKS[task_id].update({"status": "failed", "message": f"缺少必要列: {', '.join(missing_columns)}"})
            return
        processor = DataProcessor()
        processed_df = processor.process_data(df, features=[])
        records_count = 0
        for _, row in processed_df.iterrows():
            existing_data = db.query(StockData).filter(
                StockData.stock_id == stock_id,
                StockData.date == row['date']
            ).first()
            if not existing_data:
                new_data = StockData(
                    stock_id=stock_id,
                    date=row['date'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    adj_close=row.get('adj_close', row['close'])
                )
                db.add(new_data)
                records_count += 1
        stock.last_updated = datetime.now()
        if records_count > 0:
            result = db.query(
                func.count(StockData.id).label('total_records'),
                func.min(StockData.date).label('first_date'),
                func.max(StockData.date).label('last_date')
            ).filter(StockData.stock_id == stock_id).first()
            stock.total_records = result.total_records or 0
            stock.first_date = result.first_date
            stock.last_date = result.last_date
        db.commit()
        UPDATE_TASKS[task_id].update({
            "status": "completed",
            "message": f"成功更新 {records_count} 条 {stock.symbol} 的数据记录",
            "data": {
                "symbol": stock.symbol,
                "name": stock.name,
                "records_count": records_count,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    except Exception as e:
        db.rollback()
        UPDATE_TASKS[task_id].update({"status": "failed", "message": str(e)})
    finally:
        db.close()


@router.post("/fetch", status_code=status.HTTP_201_CREATED)
async def fetch_stock_data(
    request: FetchStockDataRequest,
    db: Session = Depends(get_db)
):
    symbol = request.symbol
    name = request.name
    type = request.type
    source_id = request.source_id
    start_date = request.start_date
    end_date = request.end_date
    """自动抓取股票数据并导入到数据库"""
    try:
        logger.info(f"开始自动抓取股票数据: {symbol} ({name})")
        
        # 设置默认日期范围
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            logger.info(f"使用默认开始日期: {start_date}")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"使用默认结束日期: {end_date}")
        
        # 检查数据源是否存在
        data_source = db.query(DataSource).filter(DataSource.id == source_id).first()
        if not data_source:
            raise HTTPException(status_code=404, detail=f"数据源ID {source_id} 不存在")
        
        # 根据数据源名称确定使用哪个数据抓取器
        source_name = data_source.name.lower()
        
        if 'akshare' in source_name or '抓取' in source_name:
            # AkShare抓取数据源
            fetch_source = 'akshare'
        elif '用户上传' in source_name or 'user' in source_name:
            # 用户上传的数据，使用akshare抓取（因为目前只支持akshare）
            fetch_source = 'akshare'
        else:
            # 默认使用akshare
            fetch_source = 'akshare'
        
        logger.info(f"使用数据源: {fetch_source} 抓取数据")
        
        # 检查数据源是否可用
        available_sources = data_manager.get_available_sources()
        if fetch_source not in available_sources:
            raise HTTPException(
                status_code=400, 
                detail=f"数据源 {fetch_source} 不可用，可用数据源: {', '.join(available_sources)}"
            )
        
        # 抓取数据
        file_path = data_manager.fetch_stock_data(fetch_source, symbol, start_date, end_date)
        
        if not file_path:
            raise HTTPException(status_code=500, detail=f"抓取股票 {symbol} 数据失败")
        
        logger.info(f"数据抓取成功，文件路径: {file_path}")
        
        # 读取抓取的数据
        try:
            df = pd.read_csv(file_path)
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            
            # 检查必须的列是否存在
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise HTTPException(
                    status_code=400, 
                    detail=f"抓取的数据缺少必需的列: {', '.join(missing_columns)}"
                )
            
            # 检查数据是否为空
            if df.empty:
                raise HTTPException(status_code=400, detail=f"抓取的数据为空，请检查股票代码 {symbol} 是否正确")
            
            # 检查日期格式
            try:
                df['date'] = pd.to_datetime(df['date'])
            except Exception:
                raise HTTPException(status_code=400, detail="抓取的数据中日期格式无效")
            
            # 处理数据
            processor = DataProcessor()
            processed_df = processor.process_data(df, features=[])
            
            # 检查股票是否已存在
            stock = db.query(Stock).filter(Stock.symbol == symbol).first()
            
            if not stock:
                # 创建新股票记录
                stock = Stock(
                    symbol=symbol,
                    name=name,
                    type=type,
                    source_id=source_id,
                    last_updated=datetime.now()
                )
                db.add(stock)
                db.commit()
                db.refresh(stock)
                logger.info(f"创建新股票记录: {symbol} ({name})")
            else:
                # 更新现有股票
                stock.name = name
                stock.type = type
                stock.source_id = source_id
                stock.last_updated = datetime.now()
                db.commit()
                logger.info(f"更新现有股票记录: {symbol} ({name})")
            
            # 清除该股票的现有数据（替换数据）
            deleted_count = db.query(StockData).filter(StockData.stock_id == stock.id).delete()
            db.commit()  # 确保删除操作提交
            logger.info(f"清除现有数据: {deleted_count} 条记录")
            
            # 检查数据中是否有重复日期
            original_count = len(processed_df)
            duplicate_count = processed_df.duplicated(subset=['date']).sum()
            if duplicate_count > 0:
                logger.warning(f"发现重复日期数据，将去重处理: {duplicate_count} 条重复记录")
                processed_df = processed_df.drop_duplicates(subset=['date'], keep='last')
                logger.info(f"去重后数据行数: {len(processed_df)} (原始: {original_count})")
            else:
                logger.info(f"数据无重复日期，保持原始行数: {original_count}")
            
            # 导入新数据
            data_records = []
            for _, row in processed_df.iterrows():
                stock_data = StockData(
                    stock_id=stock.id,
                    date=row['date'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    adj_close=row.get('adj_close', row['close'])
                )
                data_records.append(stock_data)
            
            # 批量插入数据
            try:
                db.bulk_save_objects(data_records)
                db.commit()
            except Exception as e:
                logger.error(f"批量插入数据失败: {str(e)}")
                db.rollback()
                raise e
            
            # 更新股票的统计信息（总记录数、开始日期、结束日期）
            update_stock_statistics(db, stock.id)
            
            logger.info(f"成功导入 {len(data_records)} 条数据记录")
            
            return {
                "status": "success",
                "message": f"成功抓取并导入 {len(data_records)} 条 {symbol} 的数据记录",
                "data": {
                    "symbol": symbol,
                    "name": name,
                    "records_count": len(data_records),
                    "date_range": {
                        "start": processed_df['date'].min().strftime('%Y-%m-%d'),
                        "end": processed_df['date'].max().strftime('%Y-%m-%d')
                    },
                    "source": fetch_source
                }
            }
            
        except pd.errors.EmptyDataError:
            raise HTTPException(status_code=400, detail="抓取的数据为空")
        except pd.errors.ParserError:
            raise HTTPException(status_code=400, detail="抓取的数据格式无效")
        except Exception as e:
            logger.error(f"处理抓取数据时发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"处理抓取数据时发生错误: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"自动抓取数据时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"自动抓取数据时发生错误: {str(e)}")

@router.get("/download/{stock_id}")
async def download_stock_data(stock_id: int, db: Session = Depends(get_db)):
    """下载指定股票的数据为CSV文件"""
    try:
        # 检查股票是否存在
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"股票ID {stock_id} 不存在")
        
        # 获取股票数据
        data = db.query(StockData).filter(StockData.stock_id == stock_id).order_by(StockData.date).all()
        if not data:
            raise HTTPException(status_code=404, detail=f"股票 {stock.symbol} 没有可用数据")
        6
        # 创建CSV文件
        output_file = os.path.join(PROCESSED_DATA_DIR, f"{stock.symbol}_{datetime.now().strftime('%Y%m%d')}.csv")
        
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in data:
                writer.writerow({
                    'date': record.date.strftime('%Y-%m-%d'),
                    'open': record.open,
                    'high': record.high,
                    'low': record.low,
                    'close': record.close,
                    'volume': record.volume,
                    'adj_close': record.adj_close
                })
        
        # 返回文件下载响应
        return FileResponse(
            path=output_file,
            filename=f"{stock.symbol}_{datetime.now().strftime('%Y%m%d')}.csv",
            media_type='text/csv'
        )
    
    except Exception as e:
        logger.error(f"下载股票数据时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载股票数据时发生错误: {str(e)}")

@router.delete("/delete/{stock_id}", status_code=status.HTTP_200_OK)
async def delete_stock_data(stock_id: int, db: Session = Depends(get_db)):
    """删除指定股票的所有数据"""
    try:
        # 检查股票是否存在
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"股票ID {stock_id} 不存在")
        
        # 获取要删除的数据记录数
        data_count = db.query(StockData).filter(StockData.stock_id == stock_id).count()
        
        # 删除股票数据
        db.query(StockData).filter(StockData.stock_id == stock_id).delete()
        
        # 删除股票记录
        db.delete(stock)
        db.commit()
        
        return {
            "status": "success",
            "message": f"成功删除股票 {stock.symbol} 及其 {data_count} 条数据记录"
        }
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"删除股票数据时发生数据库错误: {str(e)}")
        raise HTTPException(status_code=500, detail="删除股票数据时发生数据库错误")
    except Exception as e:
        logger.error(f"删除股票数据时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除股票数据时发生错误: {str(e)}")

@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_stock_data(
    symbols: str = Form(..., description="要更新的股票代码"),
    source_id: Optional[int] = Form(..., description="数据源ID"),
    db: Session = Depends(get_db)
):
    """从数据源更新指定股票的市场数据"""
    try:
        # 检查数据源
        if source_id:
            data_source = db.query(DataSource).filter(DataSource.id == source_id).first()
            if not data_source:
                raise HTTPException(status_code=404, detail=f"数据源ID {source_id} 不存在")
        
        # 初始化数据获取器
        fetcher = DataFetcher()
        
        results = []
        symbols_list = [symbols]  # 把单个字符串转换为列表
        
        for symbol in symbols_list:
            # 检查股票是否存在
            stock = db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                results.append({
                    "symbol": symbol,
                    "status": "error",
                    "message": "股票不存在"
                })
                continue
            
            try:
                # 获取最新数据
                new_data = fetcher.fetch_data(
                    symbol=symbol, 
                    start_date=(datetime.now() - pd.Timedelta(days=30)).strftime("%Y-%m-%d"),
                    end_date=datetime.now().strftime("%Y-%m-%d"),
                    data_source="yahoo" if "." not in symbol else "akshare"
                )
                
                if new_data.empty:
                    results.append({
                        "symbol": symbol,
                        "status": "error",
                        "message": "无法获取数据"
                    })
                    continue
                
                # 处理数据
                processor = DataProcessor()
                processed_data = processor.process_data(new_data, features=[])
                
                # 获取最新的数据日期
                latest_date = db.query(StockData.date)\
                    .filter(StockData.stock_id == stock.id)\
                    .order_by(StockData.date.desc())\
                    .first()
                
                if latest_date:
                    # 过滤出新数据
                    new_records = processed_data[processed_data['date'] > latest_date[0]]
                else:
                    new_records = processed_data
                
                # 没有新数据
                if new_records.empty:
                    results.append({
                        "symbol": symbol,
                        "status": "success",
                        "message": "数据已是最新",
                        "new_records": 0
                    })
                    continue
                
                # 导入新数据
                data_records = []
                for _, row in new_records.iterrows():
                    stock_data = StockData(
                        stock_id=stock.id,
                        date=row['date'],
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume'],
                        adj_close=row.get('adj_close', row['close'])
                    )
                    data_records.append(stock_data)
                
                # 批量插入数据
                db.bulk_save_objects(data_records)
                
                # 更新股票记录
                stock.last_updated = datetime.now()
                db.commit()
                
                results.append({
                    "symbol": symbol,
                    "status": "success",
                    "message": f"成功更新数据",
                    "new_records": len(data_records)
                })
                
            except Exception as e:
                logger.error(f"更新股票 {symbol} 数据时发生错误: {str(e)}")
                results.append({
                    "symbol": symbol,
                    "status": "error",
                    "message": f"更新失败: {str(e)}"
                })
        
        return {
            "status": "success",
            "results": results
        }
    
    except Exception as e:
        logger.error(f"刷新股票数据时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刷新股票数据时发生错误: {str(e)}")

@router.post("/update-all", status_code=status.HTTP_200_OK)
async def update_all_stocks_data(db: Session = Depends(get_db)):
    """一键更新所有股票数据"""
    try:
        logger.info("开始一键更新所有股票数据")
        
        # 获取所有股票
        stocks = db.query(Stock).all()
        if not stocks:
            return {
                "status": "success",
                "message": "没有找到任何股票数据",
                "results": []
            }
        
        results = []
        success_count = 0
        error_count = 0
        
        for stock in stocks:
            try:
                logger.info(f"正在更新股票: {stock.symbol} ({stock.name})")
                
                # 查找该股票的最新数据日期
                latest_data = db.query(StockData).filter(
                    StockData.stock_id == stock.id
                ).order_by(StockData.date.desc()).first()
                
                if not latest_data:
                    results.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "status": "skipped",
                        "message": "该股票没有数据记录，请先抓取初始数据"
                    })
                    continue
                
                # 计算开始日期（最后数据日期的下一天）
                last_date = latest_data.date
                start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
                end_date = datetime.now().strftime("%Y-%m-%d")
                
                # 检查是否需要更新
                if start_date > end_date:
                    results.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "status": "success",
                        "message": "数据已是最新，无需更新",
                        "records_count": 0
                    })
                    success_count += 1
                    continue
                
                # 获取数据源信息
                data_source = db.query(DataSource).filter(DataSource.id == stock.source_id).first()
                if not data_source:
                    results.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "status": "error",
                        "message": f"数据源ID {stock.source_id} 不存在"
                    })
                    error_count += 1
                    continue
                
                # 根据数据源名称选择抓取器
                source_name = data_source.name.lower()
                if 'akshare' in source_name or '抓取' in source_name:
                    fetch_source = 'akshare'
                elif '用户上传' in source_name or 'user' in source_name:
                    fetch_source = 'akshare'
                else:
                    fetch_source = 'akshare'
                
                # 检查数据源是否可用
                available_sources = data_manager.get_available_sources()
                if fetch_source not in available_sources:
                    results.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "status": "error",
                        "message": f"数据源 {fetch_source} 不可用"
                    })
                    error_count += 1
                    continue
                
                # 抓取数据到文件并读取
                file_path = data_manager.fetch_stock_data(fetch_source, stock.symbol, start_date, end_date)
                if not file_path:
                    results.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "status": "success",
                        "message": "在指定日期范围内没有新数据（可能是周末或节假日）",
                        "records_count": 0
                    })
                    success_count += 1
                    continue
                
                # 读取抓取的数据
                df = pd.read_csv(file_path)
                required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                
                # 检查必须的列是否存在
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    results.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "status": "error",
                        "message": f"抓取的数据缺少必需的列: {', '.join(missing_columns)}"
                    })
                    error_count += 1
                    continue
                
                # 检查数据是否为空
                if df.empty:
                    results.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "status": "success",
                        "message": "在指定日期范围内没有新数据",
                        "records_count": 0
                    })
                    success_count += 1
                    continue
                
                # 检查日期格式
                try:
                    df['date'] = pd.to_datetime(df['date'])
                except Exception:
                    results.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "status": "error",
                        "message": "抓取的数据中日期格式无效"
                    })
                    error_count += 1
                    continue
                
                # 处理数据
                processor = DataProcessor()
                processed_df = processor.process_data(df, features=[])
                
                # 导入新数据到数据库
                records_count = 0
                for _, row in processed_df.iterrows():
                    # 检查是否已存在该日期的数据
                    existing_data = db.query(StockData).filter(
                        StockData.stock_id == stock.id,
                        StockData.date == row['date']
                    ).first()
                    
                    if not existing_data:
                        # 创建新数据记录
                        new_data = StockData(
                            stock_id=stock.id,
                            date=row['date'],
                            open=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row['volume'],
                            adj_close=row.get('adj_close', row['close'])
                        )
                        db.add(new_data)
                        records_count += 1
                
                # 更新股票的最后更新时间和统计信息
                stock.last_updated = datetime.now()
                
                # 更新股票的统计信息（总记录数、开始日期、结束日期）
                if records_count > 0:
                    # 查询最新的统计信息
                    result = db.query(
                        func.count(StockData.id).label('total_records'),
                        func.min(StockData.date).label('first_date'),
                        func.max(StockData.date).label('last_date')
                    ).filter(StockData.stock_id == stock.id).first()
                    
                    stock.total_records = result.total_records or 0
                    stock.first_date = result.first_date
                    stock.last_date = result.last_date
                
                db.commit()
                
                results.append({
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "status": "success",
                    "message": f"成功更新 {records_count} 条数据记录",
                    "records_count": records_count
                })
                success_count += 1
                
                logger.info(f"成功更新 {records_count} 条 {stock.symbol} 的数据记录")
                
            except Exception as e:
                logger.error(f"更新股票 {stock.symbol} 数据时发生错误: {str(e)}")
                results.append({
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "status": "error",
                    "message": f"更新失败: {str(e)}"
                })
                error_count += 1
                db.rollback()  # 回滚当前股票的事务
        
        logger.info(f"一键更新完成: 成功 {success_count} 个，失败 {error_count} 个")
        
        return {
            "status": "success",
            "message": f"一键更新完成: 成功 {success_count} 个，失败 {error_count} 个",
            "summary": {
                "total": len(stocks),
                "success": success_count,
                "error": error_count
            },
            "results": results
        }
        
    except Exception as e:
        logger.error(f"一键更新所有股票数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"一键更新所有股票数据失败: {str(e)}")

@router.get("/chart/{stock_id}")
async def get_stock_chart_data(stock_id: int, db: Session = Depends(get_db)):
    """获取股票数据用于绘制K线图"""
    try:
        # 检查股票是否存在
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"股票ID {stock_id} 不存在")
        
        # 获取股票数据
        data = db.query(StockData).filter(StockData.stock_id == stock_id).order_by(StockData.date).all()
        if not data:
            raise HTTPException(status_code=404, detail=f"股票 {stock.symbol} 没有可用数据")
        
        # 格式化为K线图数据格式
        chart_data = [
            {
                "time": record.date.strftime('%Y-%m-%d'),
                "open": float(record.open),
                "high": float(record.high),
                "low": float(record.low),
                "close": float(record.close),
                "volume": int(record.volume)
            }
            for record in data
        ]
        
        return {
            "status": "success",
            "symbol": stock.symbol,
            "name": stock.name,
            "data": chart_data
        }
    
    except Exception as e:
        logger.error(f"获取股票图表数据时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取股票图表数据时发生错误: {str(e)}")

@router.post("/update-all/async", status_code=status.HTTP_202_ACCEPTED)
async def update_all_stocks_data_async():
    """异步一键更新所有股票数据，立即返回任务ID，后台线程执行"""
    task_id = str(uuid4())
    UPDATE_ALL_TASKS[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "message": "任务已提交",
        "total": 0,
        "processed": 0,
        "success": 0,
        "error": 0,
        "skipped": 0,
    }
    import threading
    threading.Thread(target=_update_all_runner, args=(task_id,), daemon=True).start()
    return {"status": "accepted", "task_id": task_id, "message": "一键更新任务已启动"}

@router.get("/update-all-tasks/{task_id}", status_code=status.HTTP_200_OK)
async def get_update_all_task_status(task_id: str = Path(..., description="任务ID")):
    task = UPDATE_ALL_TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

from ..models.data_models import get_session

def _update_all_runner(task_id: str):
    """后台执行一键更新，逐股处理并更新进度"""
    UPDATE_ALL_TASKS[task_id].update({"status": "running", "message": "正在更新"})
    db = get_session()
    try:
        stocks = db.query(Stock).all()
        UPDATE_ALL_TASKS[task_id]["total"] = len(stocks)
        for stock in stocks:
            try:
                latest = db.query(StockData).filter(StockData.stock_id == stock.id).order_by(StockData.date.desc()).first()
                if not latest:
                    UPDATE_ALL_TASKS[task_id]["skipped"] += 1
                    UPDATE_ALL_TASKS[task_id]["processed"] += 1
                    continue
                start_date = (latest.date + timedelta(days=1)).strftime("%Y-%m-%d")
                end_date = datetime.now().strftime("%Y-%m-%d")
                if start_date > end_date:
                    UPDATE_ALL_TASKS[task_id]["success"] += 1
                    UPDATE_ALL_TASKS[task_id]["processed"] += 1
                    continue
                # 获取数据源
                data_source = db.query(DataSource).filter(DataSource.id == stock.source_id).first()
                if not data_source:
                    UPDATE_ALL_TASKS[task_id]["error"] += 1
                    UPDATE_ALL_TASKS[task_id]["processed"] += 1
                    continue
                # 根据数据源名称选择抓取器
                source_name = data_source.name.lower()
                if 'akshare' in source_name or '抓取' in source_name:
                    fetch_source = 'akshare'
                elif '用户上传' in source_name or 'user' in source_name:
                    fetch_source = 'akshare'
                else:
                    fetch_source = 'akshare'
                
                # 检查数据源是否可用
                available_sources = data_manager.get_available_sources()
                if fetch_source not in available_sources:
                    UPDATE_ALL_TASKS[task_id]["error"] += 1
                    UPDATE_ALL_TASKS[task_id]["processed"] += 1
                    continue
                
                # 抓取数据到文件并读取
                file_path = data_manager.fetch_stock_data(fetch_source, stock.symbol, start_date, end_date)
                if not file_path:
                    UPDATE_ALL_TASKS[task_id]["skipped"] += 1
                    UPDATE_ALL_TASKS[task_id]["processed"] += 1
                    continue
                df = pd.read_csv(file_path)
                # 校验列
                required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    UPDATE_ALL_TASKS[task_id]["error"] += 1
                    UPDATE_ALL_TASKS[task_id]["processed"] += 1
                    continue
                # 空数据视为成功（无新数据）
                if df.empty:
                    UPDATE_ALL_TASKS[task_id]["success"] += 1
                    UPDATE_ALL_TASKS[task_id]["processed"] += 1
                    continue
                # 转换日期
                try:
                    df['date'] = pd.to_datetime(df['date'])
                except Exception:
                    UPDATE_ALL_TASKS[task_id]["error"] += 1
                    UPDATE_ALL_TASKS[task_id]["processed"] += 1
                    continue
                # 处理数据，与同步逻辑保持一致
                processor = DataProcessor()
                processed_df = processor.process_data(df, features=[])
                # 去重插入，避免违反 (stock_id, date) 唯一约束
                records_count = 0
                for _, row in processed_df.iterrows():
                    existing = db.query(StockData).filter(
                        StockData.stock_id == stock.id,
                        StockData.date == row['date']
                    ).first()
                    if not existing:
                        new_data = StockData(
                            stock_id=stock.id,
                            date=row['date'],
                            open=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row['volume'],
                            adj_close=row.get('adj_close', row['close'])
                        )
                        db.add(new_data)
                        records_count += 1
                stock.last_updated = datetime.now()
                # 更新统计信息（仅在有新增记录时）
                if records_count > 0:
                    result = db.query(
                        func.count(StockData.id).label('total_records'),
                        func.min(StockData.date).label('first_date'),
                        func.max(StockData.date).label('last_date')
                    ).filter(StockData.stock_id == stock.id).first()
                    stock.total_records = result.total_records or 0
                    stock.first_date = result.first_date
                    stock.last_date = result.last_date
                db.commit()
                UPDATE_ALL_TASKS[task_id]["success"] += 1
                UPDATE_ALL_TASKS[task_id]["processed"] += 1
            except Exception as e:
                logger.error(f"一键更新处理股票 {stock.symbol} 失败: {str(e)}")
                UPDATE_ALL_TASKS[task_id]["error"] += 1
                UPDATE_ALL_TASKS[task_id]["processed"] += 1
        UPDATE_ALL_TASKS[task_id].update({
            "status": "completed",
            "message": "一键更新完成"
        })
    except Exception as e:
        UPDATE_ALL_TASKS[task_id].update({
            "status": "failed",
            "message": f"一键更新失败: {str(e)}"
        })
    finally:
        db.close()