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
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # 初始化数据库
    init_db()
    logger.info("数据库已初始化")
    
    # 初始化默认数据源
    init_default_data()
    
    # 启动API服务
    logger.info("启动API服务...")
    uvicorn.run(
        "src.backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG
    ) 