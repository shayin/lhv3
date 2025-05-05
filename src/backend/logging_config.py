import logging
import os
from datetime import datetime

def setup_logging(log_level=logging.INFO):
    """配置日志记录"""
    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志文件名
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'app_{today}.log')
    
    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # 配置特定模块的日志级别
    logging.getLogger('src.backend.strategy').setLevel(log_level)
    logging.getLogger('src.backend.backtest').setLevel(log_level)
    logging.getLogger('src.backend.api').setLevel(log_level)
    
    logging.info(f"日志配置完成，日志文件: {log_file}，日志级别: {logging.getLevelName(log_level)}")
    
def set_log_level(level):
    """
    设置日志级别
    
    Args:
        level: 日志级别，可以是字符串（'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'）
              或者对应的日志级别常量
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 更新处理器的级别
    for handler in root_logger.handlers:
        handler.setLevel(level)
    
    logging.info(f"日志级别已设置为: {logging.getLevelName(level)}") 