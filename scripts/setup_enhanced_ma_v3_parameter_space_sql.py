#!/usr/bin/env python3
"""
使用直接SQL命令为增强型MA策略V3设置参数空间
"""

import sqlite3
import os
import datetime

# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(project_root, 'backtesting.db')

def setup_parameter_space_sql():
    """使用SQL命令为增强型MA策略V3设置参数空间"""
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"连接到数据库: {db_path}")
    
    # 策略ID - 增强型MA策略V3
    strategy_id = 12
    
    # 删除现有的参数空间配置（如果存在）
    cursor.execute(
        "DELETE FROM strategy_parameter_spaces WHERE strategy_id = ?", 
        (strategy_id,)
    )
    
    print(f"已删除策略ID {strategy_id} 的现有参数空间配置")
    
    # 定义参数空间配置
    parameter_spaces = [
        ('n1', 'int', 3, 15, 1, '短期移动平均线周期'),
        ('n2', 'int', 10, 30, 5, '中期移动平均线周期'),
        ('n3', 'int', 20, 50, 5, '长期移动平均线周期'),
        ('position_per_stage', 'float', 0.1, 0.5, 0.1, '每阶段建仓比例'),
        ('max_total_position', 'float', 0.5, 1.0, 0.1, '最大总仓位')
    ]
    
    # 添加参数空间配置
    for space in parameter_spaces:
        cursor.execute(
            """
            INSERT INTO strategy_parameter_spaces 
            (strategy_id, parameter_name, parameter_type, min_value, max_value, step_size, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (strategy_id,) + space
        )
    
    # 提交更改
    conn.commit()
    print(f"成功添加 {len(parameter_spaces)} 个参数空间配置")
    
    # 验证添加结果
    cursor.execute(
        "SELECT parameter_name, parameter_type, min_value, max_value, step_size FROM strategy_parameter_spaces WHERE strategy_id = ?",
        (strategy_id,)
    )
    results = cursor.fetchall()
    print(f"验证结果: 找到 {len(results)} 个参数空间配置")
    for row in results:
        print(f"  - {row}")
    
    # 关闭连接
    conn.close()
    print('完成')

if __name__ == "__main__":
    setup_parameter_space_sql()