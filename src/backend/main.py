import uvicorn
import logging
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 使用DEBUG级别，输出详细日志
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# 设置相关模块的日志级别
logging.getLogger('src.backend.strategy').setLevel(logging.DEBUG)
logging.getLogger('src.backend.backtest').setLevel(logging.DEBUG)
logging.getLogger('src.backend.api').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("系统启动中...")
    
    # 初始化数据库
    from src.backend.models import init_db
    init_db()
    logger.info("数据库已初始化")
    
    # 初始化默认数据源
    from src.backend.models.init_data import init_default_data
    init_default_data()
    
    # 导入API应用
    logger.info("加载API应用...")
    try:
        from src.backend.api.app import app
        
        if app is None:
            logger.error("API应用加载失败，app对象为None")
            sys.exit(1)
        
        # 路由已在app.py中注册，无需重复注册
        logger.info("路由已在app.py中预配置完成")
        
        # 启动API服务
        logger.info("启动API服务...")
        logger.info("=" * 50)
        
        uvicorn.run(
            app,  # 直接使用app对象而不是字符串路径
            host="0.0.0.0",
            port=9001,  # 使用8001端口避免冲突
            reload=False,  # 关闭热重载，因为我们直接传递了app实例
            log_level="debug"  # uvicorn日志也设为debug级别
        )
    except ImportError as e:
        logger.error(f"无法导入API应用: {e}")
        sys.exit(1)