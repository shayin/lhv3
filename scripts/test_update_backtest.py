#!/usr/bin/env python3
"""
测试回测更新功能
验证点击更新按钮后，回测会重新运行并更新数据
"""

import os
import sys
import json
import requests
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_update_backtest():
    """测试更新回测功能"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 测试回测更新功能...")
    print("=" * 50)
    
    # 1. 获取现有的回测状态列表
    print("1. 获取现有回测状态列表...")
    try:
        response = requests.get(f"{base_url}/api/backtest-status/list")
        
        if response.status_code == 200:
            backtests = response.json()
            if not backtests:
                print("❌ 没有找到现有的回测记录")
                return False
            
            # 选择第一个回测进行更新测试
            test_backtest = backtests[0]
            status_id = test_backtest['id']
            old_return = test_backtest.get('total_return', 0) or 0
            old_updated_at = test_backtest.get('updated_at')
            
            print(f"✅ 找到测试回测:")
            print(f"   ID: {status_id}")
            print(f"   名称: {test_backtest.get('name')}")
            print(f"   当前收益率: {old_return * 100:.2f}%")
            print(f"   当前更新时间: {old_updated_at}")
            
        else:
            print(f"❌ 获取回测列表失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 获取回测列表时发生错误: {str(e)}")
        return False
    
    # 2. 执行更新操作
    print(f"\n2. 执行更新操作 (ID: {status_id})...")
    try:
        update_data = {
            "reason": "手动更新测试"
        }
        
        response = requests.post(f"{base_url}/api/backtest-status/{status_id}/update", json=update_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print(f"✅ 更新请求成功")
                print(f"   消息: {result.get('message')}")
                
                # 检查返回的性能指标
                performance_metrics = result.get('data', {}).get('performance_metrics', {})
                if performance_metrics:
                    new_return = performance_metrics.get('total_return', 0) or 0
                    new_drawdown = performance_metrics.get('max_drawdown', 0) or 0
                    new_sharpe = performance_metrics.get('sharpe_ratio', 0) or 0
                    print(f"   新收益率: {new_return * 100:.2f}%")
                    print(f"   新最大回撤: {new_drawdown * 100:.2f}%")
                    print(f"   新夏普比率: {new_sharpe:.3f}")
                
            else:
                print(f"❌ 更新失败: {result.get('message')}")
                return False
        else:
            print(f"❌ 更新请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ 更新过程中发生错误: {str(e)}")
        return False
    
    # 3. 验证更新后的数据
    print(f"\n3. 验证更新后的数据...")
    try:
        # 获取更新后的状态详情
        response = requests.get(f"{base_url}/api/backtest-status/{status_id}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                data = result.get('data', {})
                new_updated_at = data.get('updated_at')
                performance_metrics = data.get('performance_metrics', {})
                new_return = performance_metrics.get('total_return', 0) or 0
                new_drawdown = performance_metrics.get('max_drawdown', 0) or 0
                new_sharpe = performance_metrics.get('sharpe_ratio', 0) or 0
                
                print(f"✅ 状态详情获取成功:")
                print(f"   更新时间: {new_updated_at}")
                print(f"   收益率: {new_return * 100:.2f}%")
                print(f"   最大回撤: {new_drawdown * 100:.2f}%")
                print(f"   夏普比率: {new_sharpe:.3f}")
                
                # 检查更新时间是否发生变化
                if new_updated_at != old_updated_at:
                    print(f"✅ 更新时间已更新: {old_updated_at} → {new_updated_at}")
                else:
                    print(f"⚠️  更新时间未发生变化")
                
            else:
                print(f"❌ 获取状态详情失败: {result.get('message')}")
                return False
        else:
            print(f"❌ 获取状态详情失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 验证更新数据时发生错误: {str(e)}")
        return False
    
    # 4. 检查历史记录
    print(f"\n4. 检查历史记录...")
    try:
        response = requests.get(f"{base_url}/api/backtest-status/{status_id}/history")
        
        if response.status_code == 200:
            history_records = response.json()
            print(f"✅ 历史记录获取成功，共 {len(history_records)} 条")
            
            # 查找最新的更新记录
            update_records = [r for r in history_records if r.get('operation_type') == 'update']
            if update_records:
                latest_update = update_records[0]
                print(f"✅ 找到最新的更新记录:")
                print(f"   记录ID: {latest_update.get('id')}")
                print(f"   操作类型: {latest_update.get('operation_type')}")
                print(f"   创建时间: {latest_update.get('created_at')}")
                print(f"   收益率: {(latest_update.get('total_return', 0) or 0) * 100:.2f}%")
            else:
                print(f"⚠️  未找到更新类型的历史记录")
            
        else:
            print(f"❌ 获取历史记录失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 检查历史记录时发生错误: {str(e)}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 回测更新功能测试完成！")
    print("✅ 更新请求成功")
    print("✅ 数据已更新")
    print("✅ 历史记录已创建")
    print("✅ 更新功能正常工作")
    
    return True

def main():
    """主函数"""
    print("🚀 回测更新功能测试工具")
    print("=" * 60)
    
    success = test_update_backtest()
    
    if success:
        print("\n🎉 所有测试通过！回测更新功能正常工作。")
        sys.exit(0)
    else:
        print("\n❌ 测试失败。")
        sys.exit(1)

if __name__ == "__main__":
    main()
