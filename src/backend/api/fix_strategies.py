import sys
import os
import sqlite3
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.config import DATABASE_URL

def fix_strategies_table():
    """修复strategies表的问题"""
    print(f"数据库URL: {DATABASE_URL}")
    
    # 从DATABASE_URL中提取数据库文件路径
    db_path = DATABASE_URL.replace("sqlite:///", "").replace("./", "")
    print(f"数据库文件路径: {db_path}")
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查表结构
        print("检查strategies表结构...")
        cursor.execute("PRAGMA table_info(strategies)")
        columns = cursor.fetchall()
        print(f"当前表结构: {columns}")
        
        # 检查是否有数据
        cursor.execute("SELECT COUNT(*) FROM strategies")
        count = cursor.fetchone()[0]
        print(f"表中有 {count} 条记录")
        
        if count > 0:
            cursor.execute("SELECT * FROM strategies")
            data = cursor.fetchall()
            print(f"表数据示例: {data[0] if data else 'None'}")
        
        # 确保is_template列的默认值为0
        try:
            print("尝试更新表结构...")
            cursor.execute("ALTER TABLE strategies ADD COLUMN IF NOT EXISTS is_template BOOLEAN DEFAULT 0")
        except sqlite3.OperationalError as e:
            print(f"更新表结构时出错: {e}")
            
        # 检查SQLAlchemy可能使用的表结构名称
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%strategies%'")
        similar_tables = cursor.fetchall()
        print(f"相似的表名: {similar_tables}")
        
        # 重建表（如果需要）
        if False:  # 默认禁用，根据需要启用
            print("备份并重建表...")
            cursor.execute("ALTER TABLE strategies RENAME TO strategies_backup")
            cursor.execute("""
            CREATE TABLE strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL,
                description VARCHAR,
                code VARCHAR,
                parameters JSON,
                created_at DATETIME,
                updated_at DATETIME,
                is_template BOOLEAN DEFAULT 0
            )
            """)
            cursor.execute("INSERT INTO strategies SELECT * FROM strategies_backup")
            cursor.execute("DROP TABLE strategies_backup")
            print("表已重建")
            
        # 尝试创建一个测试记录
        print("创建测试记录...")
        test_name = f"测试策略_{datetime.now().strftime('%H%M%S')}"
        cursor.execute("""
        INSERT INTO strategies (name, description, parameters, created_at, updated_at, is_template)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            test_name,
            "通过脚本创建的测试策略",
            '{"test": true, "value": 123}',
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            0
        ))
        conn.commit()
        
        # 验证插入
        cursor.execute("SELECT * FROM strategies WHERE name=?", (test_name,))
        result = cursor.fetchone()
        print(f"新创建的测试记录: {result}")
        
        # 确保索引存在
        print("检查和创建索引...")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_strategies_name ON strategies (name)")
        
        # 最后再次检查表中的所有记录
        cursor.execute("SELECT * FROM strategies")
        all_data = cursor.fetchall()
        for row in all_data:
            print(f"记录: {row}")
        
        print("修复操作完成")
        
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_strategies_table() 