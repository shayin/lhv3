# 策略模板包初始化

# 导入并导出策略模板类
try:
    from .strategy_template import StrategyTemplate
    from .ma_crossover_strategy import MACrossoverStrategy
    
    # 为了兼容性，将MACrossoverStrategy也导出为MovingAverageCrossover
    MovingAverageCrossover = MACrossoverStrategy
    
    # 暂时提供空的类定义以满足导入需求
    class BollingerBandsStrategy(StrategyTemplate):
        """布林带策略"""
        def __init__(self, parameters=None):
            super().__init__("布林带策略", parameters or {})
    
    class MACDStrategy(StrategyTemplate):
        """MACD策略"""
        def __init__(self, parameters=None):
            super().__init__("MACD策略", parameters or {})
    
    class RSIStrategy(StrategyTemplate):
        """RSI策略"""
        def __init__(self, parameters=None):
            super().__init__("RSI策略", parameters or {})
    
except ImportError as e:
    import logging
    logging.warning(f"无法导入策略类: {e}")
    
    # 如果导入失败，提供一些占位符
    StrategyTemplate = None
    MACrossoverStrategy = None
    MovingAverageCrossover = None
    BollingerBandsStrategy = None
    MACDStrategy = None
    RSIStrategy = None

# 导出的公共API
__all__ = [
    'StrategyTemplate',
    'MACrossoverStrategy',
    'MovingAverageCrossover',
    'BollingerBandsStrategy',
    'MACDStrategy',
    'RSIStrategy'
]
