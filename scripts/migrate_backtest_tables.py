#!/usr/bin/env python3
"""
数据库迁移脚本：更新回测相关表结构
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backend.models.data_models import get_engine, init_db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_backtest_tables():
    """迁移回测相关表结构"""
    try:
        engine = get_engine()
        
        with engine.connect() as conn:
            # 1. 创建strategy_snapshots表
            logger.info("创建strategy_snapshots表...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS strategy_snapshots (
                    id INTEGER NOT NULL,
                    strategy_id INTEGER,
                    name VARCHAR,
                    description VARCHAR,
                    code TEXT,
                    parameters TEXT,
                    template VARCHAR,
                    created_at DATETIME,
                    PRIMARY KEY (id),
                    FOREIGN KEY(strategy_id) REFERENCES strategies (id)
                )
            """))
            
            # 2. 备份现有的backtests表
            logger.info("备份现有的backtests表...")
            conn.execute(text("CREATE TABLE IF NOT EXISTS backtests_backup AS SELECT * FROM backtests"))
            
            # 3. 删除现有的backtests表
            logger.info("删除现有的backtests表...")
            conn.execute(text("DROP TABLE IF EXISTS backtests"))
            
            # 4. 创建新的backtests表
            logger.info("创建新的backtests表...")
            conn.execute(text("""
                CREATE TABLE backtests (
                    id INTEGER NOT NULL,
                    name VARCHAR,
                    description VARCHAR,
                    strategy_id INTEGER,
                    strategy_snapshot_id INTEGER NOT NULL,
                    start_date DATETIME,
                    end_date DATETIME,
                    initial_capital FLOAT,
                    instruments JSON,
                    parameters JSON,
                    position_config JSON,
                    results JSON,
                    equity_curve JSON,
                    trade_records JSON,
                    performance_metrics JSON,
                    status VARCHAR,
                    created_at DATETIME,
                    completed_at DATETIME,
                    PRIMARY KEY (id),
                    FOREIGN KEY(strategy_id) REFERENCES strategies (id),
                    FOREIGN KEY(strategy_snapshot_id) REFERENCES strategy_snapshots (id)
                )
            """))
            
            # 5. 创建索引
            logger.info("创建索引...")
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_backtests_name ON backtests (name)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_backtests_id ON backtests (id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_strategy_snapshots_id ON strategy_snapshots (id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_strategy_snapshots_name ON strategy_snapshots (name)"))
            
            conn.commit()
            logger.info("数据库迁移完成！")
            
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        raise

if __name__ == "__main__":
    migrate_backtest_tables()
