#!/usr/bin/env python3
"""
测试回测保存功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from datetime import datetime

def test_backtest_save():
    """测试回测保存功能"""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("测试回测保存功能")
    print("=" * 60)
    
    # 1. 测试获取回测列表（应该为空）
    print("\n1. 获取回测列表...")
    response = requests.get(f"{base_url}/api/backtest/list")
    if response.status_code == 200:
        backtests = response.json()
        print(f"当前回测数量: {len(backtests)}")
        if backtests:
            for bt in backtests:
                print(f"  - {bt['name']} (ID: {bt['id']})")
    else:
        print(f"获取回测列表失败: {response.status_code}")
        return
    
    # 2. 测试保存回测
    print("\n2. 保存回测...")
    save_data = {
        "name": "AAPL_MA交叉策略测试",
        "description": "使用MA交叉策略对AAPL进行回测测试",
        "strategy_id": 1,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 100000,
        "instruments": ["AAPL"],
        "parameters": {
            "positionConfig": {
                "mode": "fixed",
                "defaultSize": 1.0
            }
        },
        "position_config": {
            "mode": "fixed",
            "defaultSize": 1.0
        }
    }
    
    response = requests.post(
        f"{base_url}/api/backtest/save",
        headers={"Content-Type": "application/json"},
        data=json.dumps(save_data)
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"保存成功: {result['message']}")
        print(f"回测ID: {result['data']['backtest_id']}")
        backtest_id = result['data']['backtest_id']
    else:
        print(f"保存失败: {response.status_code}")
        print(f"错误信息: {response.text}")
        return
    
    # 3. 再次获取回测列表（应该有新保存的回测）
    print("\n3. 再次获取回测列表...")
    response = requests.get(f"{base_url}/api/backtest/list")
    if response.status_code == 200:
        backtests = response.json()
        print(f"当前回测数量: {len(backtests)}")
        for bt in backtests:
            print(f"  - {bt['name']} (ID: {bt['id']})")
            print(f"    策略: {bt['strategy_name']}")
            print(f"    状态: {bt['status']}")
            print(f"    创建时间: {bt['created_at']}")
    else:
        print(f"获取回测列表失败: {response.status_code}")
    
    # 4. 测试获取回测详情
    print(f"\n4. 获取回测详情 (ID: {backtest_id})...")
    response = requests.get(f"{base_url}/api/backtest/{backtest_id}")
    if response.status_code == 200:
        result = response.json()
        if result['status'] == 'success':
            detail = result['data']
            print(f"回测名称: {detail['name']}")
            print(f"描述: {detail['description']}")
            print(f"策略: {detail['strategy_info']['name'] if detail['strategy_info'] else 'N/A'}")
            print(f"回测期间: {detail['start_date']} 至 {detail['end_date']}")
            print(f"初始资金: ${detail['initial_capital']:,.2f}")
            print(f"交易标的: {', '.join(detail['instruments'])}")
            print(f"状态: {detail['status']}")
        else:
            print(f"获取详情失败: {result.get('message', '未知错误')}")
    else:
        print(f"获取回测详情失败: {response.status_code}")
    
    # 5. 测试删除回测
    print(f"\n5. 删除回测 (ID: {backtest_id})...")
    response = requests.delete(f"{base_url}/api/backtest/{backtest_id}")
    if response.status_code == 200:
        result = response.json()
        print(f"删除成功: {result['message']}")
    else:
        print(f"删除失败: {response.status_code}")
        print(f"错误信息: {response.text}")
    
    # 6. 最终检查回测列表（应该为空）
    print("\n6. 最终检查回测列表...")
    response = requests.get(f"{base_url}/api/backtest/list")
    if response.status_code == 200:
        backtests = response.json()
        print(f"最终回测数量: {len(backtests)}")
    else:
        print(f"获取回测列表失败: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_backtest_save()
