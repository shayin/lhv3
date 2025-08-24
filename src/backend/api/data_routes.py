from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Path, status, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
import pandas as pd
import logging
from datetime import datetime
import shutil
import csv
from sqlalchemy.exc import SQLAlchemyError

from ..models import get_db, Stock, DailyPrice, DataSource, StockData
from ..config import RAW_DATA_DIR, PROCESSED_DATA_DIR
from ..data import DataFetcher, DataProcessor

# 导入数据抓取模块
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.data_manager import DataManager

logger = logging.getLogger(__name__)
router = APIRouter()

# 确保数据目录存在
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

# 初始化数据管理器
data_manager = DataManager()

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
        
        return [
            {
                "id": stock.id,
                "symbol": stock.symbol,
                "name": stock.name,
                "type": stock.type,
                "source_id": stock.source_id,
                "last_updated": stock.last_updated.isoformat() if stock.last_updated else None,
                "data_count": db.query(StockData).filter(StockData.stock_id == stock.id).count()
            }
            for stock in stocks
        ]
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

@router.post("/fetch", status_code=status.HTTP_201_CREATED)
async def fetch_stock_data(
    symbol: str = Query(..., description="股票代码"),
    name: str = Query(..., description="股票名称"),
    type: str = Query(..., description="股票类型: A股/港股/美股/期货/加密货币等"),
    source_id: int = Query(..., description="数据源ID"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD，默认为30天前"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD，默认为今天"),
    db: Session = Depends(get_db)
):
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
        if 'yahoo' in source_name:
            fetch_source = 'yahoo'
        elif 'akshare' in source_name or 'a股' in source_name:
            fetch_source = 'akshare'
        elif 'tushare' in source_name:
            fetch_source = 'tushare'
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
            logger.info(f"清除现有数据: {deleted_count} 条记录")
            
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