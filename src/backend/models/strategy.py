from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey, Text
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
    template = Column(String, nullable=True)  # 策略模板类型
    
    # 一对多关系：一个策略可以有多个回测
    backtests = relationship("Backtest", back_populates="strategy")

class StrategySnapshot(Base):
    """策略快照模型 - 保存策略的镜像"""
    __tablename__ = "strategy_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    code = Column(Text)  # 策略代码镜像
    parameters = Column(Text, nullable=True)  # 策略参数镜像，JSON字符串格式
    template = Column(String, nullable=True)  # 策略模板类型镜像
    created_at = Column(DateTime, default=datetime.now)
    
    # 多对一关系：多个快照属于一个策略
    strategy = relationship("Strategy")
    # 一对多关系：一个快照可以有多个回测
    backtests = relationship("Backtest", back_populates="strategy_snapshot")

class Backtest(Base):
    """回测模型"""
    __tablename__ = "backtests"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    
    # 策略相关
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)  # 当前策略ID（可能为空）
    strategy_snapshot_id = Column(Integer, ForeignKey("strategy_snapshots.id"), nullable=False)  # 策略快照ID
    
    # 回测参数
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    initial_capital = Column(Float)
    instruments = Column(JSON)  # 回测标的，JSON格式
    parameters = Column(JSON, nullable=True)  # 回测参数，JSON格式
    
    # 仓位控制参数
    position_config = Column(JSON, nullable=True)  # 仓位控制配置
    
    # 回测结果
    results = Column(JSON, nullable=True)  # 回测结果，JSON格式
    equity_curve = Column(JSON, nullable=True)  # 权益曲线数据
    trade_records = Column(JSON, nullable=True)  # 交易记录
    performance_metrics = Column(JSON, nullable=True)  # 性能指标
    
    # 状态和时间
    status = Column(String, default='running')  # running, completed, failed
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    strategy = relationship("Strategy", back_populates="backtests")
    strategy_snapshot = relationship("StrategySnapshot", back_populates="backtests")
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