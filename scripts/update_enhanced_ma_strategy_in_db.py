#!/usr/bin/env python3
"""
更新数据库中的增强型MA策略代码
"""

import sys
import os
import sqlite3
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def update_enhanced_ma_strategy():
    """更新数据库中的增强型MA策略代码"""
    
    # 数据库路径
    db_path = os.path.join(project_root, 'backtesting.db')
    
    # 策略代码文件路径
    strategy_file = os.path.join(project_root, 'src/backend/strategy/enhanced_ma_strategy.py')
    
    try:
        # 读取策略代码
        with open(strategy_file, 'r', encoding='utf-8') as f:
            strategy_code = f.read()
        
        print(f"已读取策略代码文件: {strategy_file}")
        print(f"代码长度: {len(strategy_code)} 字符")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查找增强型MA策略
        cursor.execute("SELECT id, name FROM strategies WHERE template = 'enhanced_ma' OR name LIKE '%增强型移动平均%'")
        strategies = cursor.fetchall()
        
        if not strategies:
            print("未找到增强型MA策略，请先运行 add_enhanced_ma_strategy_to_db.py")
            return False
        
        # 更新每个找到的策略
        for strategy_id, strategy_name in strategies:
            print(f"\n更新策略: ID={strategy_id}, 名称={strategy_name}")
            
            # 备份当前代码
            cursor.execute("SELECT code FROM strategies WHERE id = ?", (strategy_id,))
            current_code = cursor.fetchone()[0]
            
            backup_filename = f"strategy_{strategy_id}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            backup_path = os.path.join(project_root, 'backups', backup_filename)
            
            # 确保备份目录存在
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(current_code)
            print(f"已备份当前代码到: {backup_path}")
            
            # 更新策略代码
            cursor.execute("""
                UPDATE strategies 
                SET code = ?, updated_at = ?
                WHERE id = ?
            """, (strategy_code, datetime.now().isoformat(), strategy_id))
            
            print(f"已更新策略 {strategy_id} 的代码")
        
        # 提交更改
        conn.commit()
        print(f"\n成功更新了 {len(strategies)} 个增强型MA策略")
        
        # 验证更新
        for strategy_id, strategy_name in strategies:
            cursor.execute("SELECT LENGTH(code), updated_at FROM strategies WHERE id = ?", (strategy_id,))
            code_length, updated_at = cursor.fetchone()
            print(f"策略 {strategy_id}: 代码长度={code_length}, 更新时间={updated_at}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"更新策略时发生错误: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("开始更新数据库中的增强型MA策略代码...")
    success = update_enhanced_ma_strategy()
    
    if success:
        print("\n✅ 策略代码更新完成！")
    else:
        print("\n❌ 策略代码更新失败！")
        sys.exit(1)