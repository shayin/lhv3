#!/usr/bin/env python3
"""
测试前端保存功能
模拟前端调用后端API保存回测数据
"""

import os
import sys
import json
import requests
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_frontend_save_flow():
    """测试前端保存流程"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 测试前端保存流程...")
    print("=" * 50)
    
    # 1. 模拟前端运行回测
    print("1. 模拟前端运行回测...")
    backtest_payload = {
        "strategy_id": 1,
        "symbol": "AAPL",
        "start_date": "2025-01-02",
        "end_date": "2025-08-22",
        "initial_capital": 100000,
        "parameters": {
            "positionConfig": {
                "mode": "fixed",
                "defaultSize": 0.1,
                "sizes": [0.1, 0.2, 0.3],
                "dynamicMax": 0.5
            }
        },
        "commission_rate": 0.0015,
        "slippage_rate": 0.001,
        "data_source": "database",
        "features": []
    }
    
    try:
        # 运行回测
        response = requests.post(f"{base_url}/api/strategies/backtest", json=backtest_payload)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                backtest_data = result.get('data', {})
                print(f"✅ 回测运行成功")
                print(f"   总收益率: {backtest_data.get('total_return', 0) * 100:.2f}%")
                print(f"   最大回撤: {backtest_data.get('max_drawdown', 0) * 100:.2f}%")
                print(f"   夏普比率: {backtest_data.get('sharpe_ratio', 0):.3f}")
            else:
                print(f"❌ 回测失败: {result.get('message')}")
                return False
        else:
            print(f"❌ 回测请求失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 回测过程中发生错误: {str(e)}")
        return False
    
    # 2. 模拟前端保存回测（通过backtestStrategy函数）
    print("\n2. 模拟前端保存回测...")
    save_payload = {
        "strategy_id": 1,
        "symbol": "AAPL",
        "start_date": "2025-01-02",
        "end_date": "2025-08-22",
        "initial_capital": 100000,
        "parameters": {
            "positionConfig": {
                "mode": "fixed",
                "defaultSize": 0.1,
                "sizes": [0.1, 0.2, 0.3],
                "dynamicMax": 0.5
            },
            "save_backtest": True,
            "backtest_name": "前端测试回测",
            "backtest_description": "通过前端保存的回测"
        },
        "commission_rate": 0.0015,
        "slippage_rate": 0.001,
        "data_source": "database",
        "features": []
    }
    
    try:
        # 运行回测并保存
        response = requests.post(f"{base_url}/api/strategies/backtest", json=save_payload)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                data = result.get('data', {})
                if data.get('saved'):
                    print(f"✅ 回测保存成功")
                    print(f"   保存状态: {data.get('saved')}")
                else:
                    print(f"❌ 保存失败: 未返回保存状态")
                    return False
            else:
                print(f"❌ 保存失败: {result.get('message')}")
                return False
        else:
            print(f"❌ 保存请求失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 保存过程中发生错误: {str(e)}")
        return False
    
    # 3. 验证数据保存到新架构
    print("\n3. 验证数据保存到新架构...")
    try:
        response = requests.get(f"{base_url}/api/backtest-status/list")
        
        if response.status_code == 200:
            backtests = response.json()
            # 查找我们刚保存的回测
            test_backtest = None
            for bt in backtests:
                if "前端测试回测" in bt.get('name', ''):
                    test_backtest = bt
                    break
            
            if test_backtest:
                print(f"✅ 在新架构中找到保存的回测:")
                print(f"   ID: {test_backtest.get('id')}")
                print(f"   名称: {test_backtest.get('name')}")
                print(f"   收益率: {test_backtest.get('total_return', 0) * 100:.2f}%")
                print(f"   状态: {test_backtest.get('status')}")
            else:
                print(f"❌ 在新架构中未找到保存的回测")
                return False
        else:
            print(f"❌ 获取新架构列表失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 验证新架构数据时发生错误: {str(e)}")
        return False
    
    # 4. 验证数据也保存到旧架构（向后兼容）
    print("\n4. 验证数据也保存到旧架构...")
    try:
        response = requests.get(f"{base_url}/api/backtest/list")
        
        if response.status_code == 200:
            backtests = response.json()
            # 查找我们刚保存的回测
            test_backtest = None
            for bt in backtests:
                if "前端测试回测" in bt.get('name', ''):
                    test_backtest = bt
                    break
            
            if test_backtest:
                print(f"✅ 在旧架构中也找到保存的回测:")
                print(f"   ID: {test_backtest.get('id')}")
                print(f"   名称: {test_backtest.get('name')}")
                print(f"   状态: {test_backtest.get('status')}")
            else:
                print(f"❌ 在旧架构中未找到保存的回测")
                return False
        else:
            print(f"❌ 获取旧架构列表失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 验证旧架构数据时发生错误: {str(e)}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 前端保存流程测试完成！")
    print("✅ 回测运行正常")
    print("✅ 数据保存到新架构")
    print("✅ 数据也保存到旧架构（向后兼容）")
    print("✅ 前端保存功能完全正常")
    
    return True

def main():
    """主函数"""
    print("🚀 前端保存功能测试工具")
    print("=" * 60)
    
    success = test_frontend_save_flow()
    
    if success:
        print("\n🎉 所有测试通过！前端保存功能正常工作。")
        sys.exit(0)
    else:
        print("\n❌ 测试失败。")
        sys.exit(1)

if __name__ == "__main__":
    main()
