# API模块初始化

try:
    from .app import app
except ImportError as e:
    import logging
    logging.warning(f"无法导入app模块: {e}")
    app = None 