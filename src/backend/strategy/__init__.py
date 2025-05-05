# 策略模块初始化
# 在导入时确保不会因为缺少类而失败

try:
    from .base import StrategyBase
except ImportError:
    pass

try:
    from .templates import MovingAverageCrossover, BollingerBandsStrategy, MACDStrategy, RSIStrategy
except ImportError as e:
    import logging
    logging.warning(f"无法导入策略类: {e}")

# 导出公共API
__all__ = [
    'StrategyBase',
    'MovingAverageCrossover',
    'BollingerBandsStrategy',
    'MACDStrategy',
    'RSIStrategy'
] 