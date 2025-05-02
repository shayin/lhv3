from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base

class Strategy(Base):
    """策略模型"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    code = Column(String)  # 策略代码
    parameters = Column(String, nullable=True)  # 策略参数，JSON字符串格式
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_template = Column(Boolean, default=False)  # 是否为模板策略
    
    # 一对多关系：一个策略可以有多个回测
    backtests = relationship("Backtest", back_populates="strategy")

class Backtest(Base):
    """回测模型"""
    __tablename__ = "backtests"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    initial_capital = Column(Float)
    instruments = Column(JSON)  # 回测标的，JSON格式
    parameters = Column(JSON, nullable=True)  # 回测参数，JSON格式
    results = Column(JSON, nullable=True)  # 回测结果，JSON格式
    created_at = Column(DateTime, default=datetime.now)
    
    # 多对一关系：多个回测属于一个策略
    strategy = relationship("Strategy", back_populates="backtests")
    # 一对多关系：一个回测有多个交易记录
    trades = relationship("Trade", back_populates="backtest")

class Trade(Base):
    """交易记录模型"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, ForeignKey("backtests.id"))
    datetime = Column(DateTime)
    symbol = Column(String, index=True)
    direction = Column(String)  # BUY or SELL
    price = Column(Float)
    quantity = Column(Float)
    commission = Column(Float)
    
    # 多对一关系：多个交易记录属于一个回测
    backtest = relationship("Backtest", back_populates="trades") 