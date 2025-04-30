from sqlalchemy.orm import Session
from datetime import datetime

from .data_models import DataSource, get_db

def init_default_data():
    """初始化默认数据"""
    db = next(get_db())
    
    try:
        # 检查是否已经存在数据源
        existing_sources = db.query(DataSource).all()
        if not existing_sources:
            # 添加默认数据源
            default_sources = [
                DataSource(
                    name="Yahoo Finance",
                    description="雅虎财经数据，提供美股、港股等全球市场数据",
                    created_at=datetime.now()
                ),
                DataSource(
                    name="A股数据",
                    description="中国A股市场数据",
                    created_at=datetime.now()
                ),
                DataSource(
                    name="用户上传",
                    description="用户自定义上传的数据",
                    created_at=datetime.now()
                )
            ]
            
            db.add_all(default_sources)
            db.commit()
            print("已添加默认数据源")
        else:
            print(f"数据库中已存在 {len(existing_sources)} 个数据源，无需初始化")
            
    except Exception as e:
        db.rollback()
        print(f"初始化数据失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_default_data() 