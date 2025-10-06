#!/usr/bin/env python3
"""
更新V7策略的性能优化参数
添加新的性能优化参数到数据库中的V7策略
"""

import sys
import os
import json

# 添加项目路径
backend_path = os.path.join(os.path.dirname(__file__), 'src', 'backend')
sys.path.insert(0, backend_path)

from models.base import get_db, SessionLocal
from models.strategy import Strategy

def update_v7_performance_params():
    """更新V7策略的性能优化参数"""
    db = SessionLocal()
    
    try:
        # 查找V7策略
        strategies = db.query(Strategy).all()
        v7_strategy = None
        
        for strategy in strategies:
            if 'v7' in strategy.name.lower() or 'extremum_strategy_v7' in (strategy.template or ''):
                v7_strategy = strategy
                break
        
        if not v7_strategy:
            print("未找到V7策略")
            return False
        
        print(f"找到V7策略: {v7_strategy.name} (ID: {v7_strategy.id})")
        
        # 获取当前参数
        current_params = json.loads(v7_strategy.parameters) if v7_strategy.parameters else {}
        print(f"当前参数数量: {len(current_params)}")
        
        # 添加性能优化参数
        performance_params = {
            "max_extremums": 50,                # 最大极值点数量限制
            "min_extremum_distance": 3,         # 极值点之间的最小距离
            "use_scipy_optimization": True,     # 是否使用scipy优化算法
        }
        
        # 更新参数
        updated_params = current_params.copy()
        updated_params.update(performance_params)
        
        print("添加的性能优化参数:")
        for key, value in performance_params.items():
            print(f"  {key}: {value}")
        
        # 更新数据库
        v7_strategy.parameters = json.dumps(updated_params, ensure_ascii=False, indent=2)
        db.commit()
        
        print(f"✅ 成功更新V7策略参数，新参数数量: {len(updated_params)}")
        
        # 验证更新
        db.refresh(v7_strategy)
        verify_params = json.loads(v7_strategy.parameters)
        print("验证更新后的参数:")
        for key in performance_params.keys():
            if key in verify_params:
                print(f"  ✅ {key}: {verify_params[key]}")
            else:
                print(f"  ❌ {key}: 未找到")
        
        return True
            
    except Exception as e:
        print(f"❌ 更新过程中出错: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("开始更新V7策略的性能优化参数...")
    success = update_v7_performance_params()
    
    if success:
        print("\n🎉 V7策略性能优化参数更新完成！")
        print("\n性能优化说明:")
        print("- max_extremums: 限制极值点数量，避免计算过多")
        print("- min_extremum_distance: 过滤过近的极值点，提高质量")
        print("- use_scipy_optimization: 使用scipy算法，O(n²)→O(n)优化")
    else:
        print("\n❌ 更新失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    print("开始更新V7策略的性能优化参数...")
    success = update_v7_performance_params()
    
    if success:
        print("\n🎉 V7策略性能优化参数更新完成！")
        print("\n性能优化说明:")
        print("- max_extremums: 限制极值点数量，避免计算过多")
        print("- min_extremum_distance: 过滤过近的极值点，提高质量")
        print("- use_scipy_optimization: 使用scipy算法，O(n²)→O(n)优化")
    else:
        print("\n❌ 更新失败，请检查错误信息")
        sys.exit(1)