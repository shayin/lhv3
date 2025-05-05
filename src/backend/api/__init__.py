# API模块初始化

try:
    from .app import app
except ImportError as e:
    import logging
    logging.warning(f"无法导入app模块: {e}")
    app = None

# 仅在app不为None时注册路由
if app is not None:
    try:
        from .strategy_routes import router as strategy_router
        app.include_router(strategy_router)
        
        from .backtest_routes import router as backtest_router
        app.include_router(backtest_router)
    except ImportError as e:
        import logging
        logging.warning(f"无法导入路由模块: {e}") 