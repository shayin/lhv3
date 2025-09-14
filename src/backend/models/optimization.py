"""
参数优化相关的数据模型
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class StrategyParameterSpace(Base):
    """策略参数空间定义"""
    __tablename__ = "strategy_parameter_spaces"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    parameter_name = Column(String(100), nullable=False)
    parameter_type = Column(String(20), nullable=False)  # 'int', 'float', 'choice'
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    step_size = Column(Float, nullable=True)
    choices = Column(JSON, nullable=True)  # 用于choice类型
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    strategy = relationship("Strategy", back_populates="parameter_spaces")


class ParameterSet(Base):
    """参数组"""
    __tablename__ = "parameter_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=False)  # 存储参数键值对
    optimization_job_id = Column(Integer, ForeignKey("optimization_jobs.id"), nullable=True)
    status = Column(String(20), default='active')  # 'active', 'archived', 'paused'
    is_default = Column(Boolean, default=False)  # 是否为默认参数组
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    strategy = relationship("Strategy", back_populates="parameter_sets")
    optimization_job = relationship("OptimizationJob", back_populates="parameter_sets")
    performance_records = relationship("ParameterSetPerformance", back_populates="parameter_set", cascade="all, delete-orphan")


class ParameterSetPerformance(Base):
    """参数组性能记录"""
    __tablename__ = "parameter_set_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    parameter_set_id = Column(Integer, ForeignKey("parameter_sets.id"), nullable=False)
    backtest_date = Column(DateTime, nullable=False)  # 回测数据截止日期
    total_return = Column(Float, nullable=True)
    annual_return = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    trade_count = Column(Integer, nullable=True)
    ranking = Column(Integer, nullable=True)  # 在同策略参数组中的排名
    performance_score = Column(Float, nullable=True)  # 综合性能评分
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    parameter_set = relationship("ParameterSet", back_populates="performance_records")


class OptimizationJob(Base):
    """优化任务记录"""
    __tablename__ = "optimization_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    optimization_config = Column(JSON, nullable=False)  # 优化配置
    status = Column(String(20), default='running')  # 'running', 'completed', 'failed', 'cancelled'
    best_parameters = Column(JSON, nullable=True)
    best_score = Column(Float, nullable=True)
    objective_function = Column(String(50), default='sharpe_ratio')  # 优化目标函数
    total_trials = Column(Integer, default=0)
    completed_trials = Column(Integer, default=0)
    progress = Column(Float, default=0.0)  # 进度百分比
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    strategy = relationship("Strategy", back_populates="optimization_jobs")
    parameter_sets = relationship("ParameterSet", back_populates="optimization_job")
    trials = relationship("OptimizationTrial", back_populates="job", cascade="all, delete-orphan")


class OptimizationTrial(Base):
    """优化试验记录"""
    __tablename__ = "optimization_trials"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("optimization_jobs.id"), nullable=False)
    trial_number = Column(Integer, nullable=False)
    parameters = Column(JSON, nullable=False)
    objective_value = Column(Float, nullable=True)
    status = Column(String(20), default='running')  # 'running', 'completed', 'failed', 'pruned'
    execution_time = Column(Float, nullable=True)  # 执行时间(秒)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    job = relationship("OptimizationJob", back_populates="trials")


class ParameterSetMonitor(Base):
    """参数组监控设置"""
    __tablename__ = "parameter_set_monitors"
    
    id = Column(Integer, primary_key=True, index=True)
    parameter_set_id = Column(Integer, ForeignKey("parameter_sets.id"), nullable=False)
    monitor_enabled = Column(Boolean, default=True)
    update_frequency = Column(String(20), default='daily')  # 'daily', 'weekly', 'monthly'
    alert_threshold_return = Column(Float, nullable=True)  # 收益率预警阈值
    alert_threshold_drawdown = Column(Float, nullable=True)  # 回撤预警阈值
    last_updated = Column(DateTime, nullable=True)
    next_update = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    parameter_set = relationship("ParameterSet")
