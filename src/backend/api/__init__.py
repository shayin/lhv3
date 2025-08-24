# API模块初始化

try:
    from .app import app
except ImportError as e:
    import logging
    logging.warning(f"无法导入app模块: {e}")
    app = None

# 注意：路由注册已移动到app.py中，避免重复注册 