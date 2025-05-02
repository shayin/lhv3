from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

from ..config import DATABASE_URL

# 配置日志记录器
logger = logging.getLogger(__name__)

# 创建数据库引擎
engine = create_engine(DATABASE_URL)

# 添加SQL查询事件监听器
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    logger.info(f"执行SQL: {statement}")
    if parameters:
        logger.info(f"参数: {parameters}")

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    logger.info("SQL执行完成")

# 创建会话类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 

# 初始化数据库函数
def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    logger.info("数据库初始化完成，所有表已创建") 