import uvicorn
import logging
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.backend.api import app
from src.backend.models import init_db
from src.backend.models.init_data import init_default_data
from src.backend.config import DEBUG, LOG_LEVEL

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
    init_db()
    logger.info("数据库已初始化")
    
    # 初始化默认数据源
    init_default_data()
    
    # 启动API服务
    logger.info("启动API服务...")
    logger.info("=" * 50)
    
    uvicorn.run(
        "src.backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        log_level="debug"  # uvicorn日志也设为debug级别
    ) 