#!/usr/bin/env python3
"""
数据库维护脚本：更新所有股票的统计信息
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.backend.models import get_db, Stock, StockData
from sqlalchemy import func
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_all_stock_statistics():
    """更新所有股票的统计信息"""
    db = next(get_db())
    
    try:
        # 获取所有股票
        stocks = db.query(Stock).all()
        logger.info(f"找到 {len(stocks)} 只股票")
        
        updated_count = 0
        for stock in stocks:
            try:
                # 查询股票的统计信息
                result = db.query(
                    func.count(StockData.id).label('total_records'),
                    func.min(StockData.date).label('first_date'),
                    func.max(StockData.date).label('last_date')
                ).filter(StockData.stock_id == stock.id).first()
                
                # 更新股票记录
                old_total = stock.total_records
                old_first = stock.first_date
                old_last = stock.last_date
                
                stock.total_records = result.total_records or 0
                stock.first_date = result.first_date
                stock.last_date = result.last_date
                stock.last_updated = datetime.now()
                
                # 检查是否有变化
                if (old_total != stock.total_records or 
                    old_first != stock.first_date or 
                    old_last != stock.last_date):
                    updated_count += 1
                    logger.info(f"更新 {stock.symbol}: {old_total}->{stock.total_records} 条记录, "
                              f"时间范围: {old_first}~{old_last} -> {stock.first_date}~{stock.last_date}")
                
            except Exception as e:
                logger.error(f"更新股票 {stock.symbol} 统计信息失败: {str(e)}")
                continue
        
        # 提交所有更改
        db.commit()
        logger.info(f"成功更新 {updated_count} 只股票的统计信息")
        
    except Exception as e:
        logger.error(f"更新统计信息失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def show_stock_statistics():
    """显示所有股票的统计信息"""
    db = next(get_db())
    
    try:
        stocks = db.query(Stock).all()
        
        print("\n股票统计信息:")
        print("-" * 80)
        print(f"{'代码':<10} {'名称':<15} {'记录数':<8} {'开始日期':<12} {'结束日期':<12} {'最后更新':<20}")
        print("-" * 80)
        
        for stock in stocks:
            print(f"{stock.symbol:<10} {stock.name:<15} {stock.total_records:<8} "
                  f"{stock.first_date.strftime('%Y-%m-%d') if stock.first_date else 'N/A':<12} "
                  f"{stock.last_date.strftime('%Y-%m-%d') if stock.last_date else 'N/A':<12} "
                  f"{stock.last_updated.strftime('%Y-%m-%d %H:%M') if stock.last_updated else 'N/A':<20}")
        
        print("-" * 80)
        
    except Exception as e:
        logger.error(f"显示统计信息失败: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="股票统计信息维护工具")
    parser.add_argument("--update", action="store_true", help="更新所有股票的统计信息")
    parser.add_argument("--show", action="store_true", help="显示所有股票的统计信息")
    
    args = parser.parse_args()
    
    if args.update:
        logger.info("开始更新股票统计信息...")
        update_all_stock_statistics()
        logger.info("更新完成")
    
    if args.show:
        show_stock_statistics()
    
    if not args.update and not args.show:
        # 默认显示统计信息
        show_stock_statistics()
