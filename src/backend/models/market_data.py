from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class DataSource(Base):
    """数据源模型"""
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    api_url = Column(String, nullable=True)
    
    # 一对多关系：一个数据源可以有多个股票
    stocks = relationship("Stock", back_populates="data_source")

class Stock(Base):
    """股票基本信息模型"""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    name = Column(String)
    exchange = Column(String)
    industry = Column(String, nullable=True)
    listed_date = Column(Date, nullable=True)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"))
    
    # 多对一关系：多个股票属于一个数据源
    data_source = relationship("DataSource", back_populates="stocks")
    # 一对多关系：一个股票有多个价格数据
    price_data = relationship("DailyPrice", back_populates="stock")

class DailyPrice(Base):
    """每日股价数据模型"""
    __tablename__ = "daily_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    date = Column(Date, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    adjusted_close = Column(Float, nullable=True)
    
    # 多对一关系：多个价格数据属于一个股票
    stock = relationship("Stock", back_populates="price_data") 