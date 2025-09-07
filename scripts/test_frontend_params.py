#!/usr/bin/env python3
"""
测试前端参数匹配的更新功能
验证前端传递的 new_name 和 update_to_date 参数是否正确处理
"""

import sys
import os
import requests
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
API_BASE_URL = "http://localhost:8000"
TEST_NAME = "前端参数测试"

def test_frontend_params_update():
    """测试前端参数格式的更新功能"""
    print("=" * 60)
    print("测试前端参数匹配的更新功能")
    print("=" * 60)
    
    # 1. 获取现有的回测状态列表
    print("\n1. 获取回测状态列表...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/backtest-status/list")
        if response.status_code == 200:
            backtest_list = response.json()
            print(f"   找到 {len(backtest_list)} 个回测状态")
            
            if not backtest_list:
                print("   没有找到回测状态，请先创建一些回测数据")
                return False
                
            # 选择第一个回测状态进行测试
            test_status = backtest_list[0]
            status_id = test_status['id']
            original_name = test_status['name']
            original_end_date = test_status['end_date']
            
            print(f"   选择回测状态: ID={status_id}, 名称={original_name}")
            print(f"   原始结束日期: {original_end_date}")
            
        else:
            print(f"   获取回测列表失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   获取回测列表异常: {e}")
        return False
    
    # 2. 使用前端参数格式进行更新
    print(f"\n2. 使用前端参数格式更新回测状态 {status_id}...")
    
    # 模拟前端传递的参数
    update_data = {
        "new_name": f"{original_name}_前端更新",
        "update_to_date": "2017-09-01"  # 前端传递的格式
    }
    
    print(f"   更新参数: {json.dumps(update_data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/backtest-status/{status_id}/update",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   更新成功!")
            print(f"   响应状态: {result.get('status')}")
            print(f"   响应消息: {result.get('message')}")
            
            data = result.get('data', {})
            print(f"   新回测名称: {data.get('new_backtest_name')}")
            print(f"   更新范围: {data.get('update_range')}")
            print(f"   性能指标: {data.get('performance_metrics')}")
            
            # 验证更新结果
            if data.get('new_backtest_name') == f"{original_name}_前端更新":
                print("   ✅ 新名称更新正确")
            else:
                print("   ❌ 新名称更新失败")
                return False
                
            update_range = data.get('update_range', {})
            if update_range.get('end_date') == "2017-09-01":
                print("   ✅ 结束日期更新正确")
            else:
                print("   ❌ 结束日期更新失败")
                return False
                
        else:
            print(f"   更新失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"   更新异常: {e}")
        return False
    
    # 3. 验证数据库中的更新结果
    print(f"\n3. 验证数据库中的更新结果...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/backtest-status/{status_id}")
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                status_data = result.get('data', {})
                db_name = status_data.get('name')
                db_end_date = status_data.get('end_date')
                
                print(f"   数据库中的名称: {db_name}")
                print(f"   数据库中的结束日期: {db_end_date}")
                
                # 验证数据库更新
                if db_name == f"{original_name}_前端更新":
                    print("   ✅ 数据库名称更新正确")
                else:
                    print("   ❌ 数据库名称更新失败")
                    return False
                    
                # 处理ISO格式的日期比较
                if db_end_date.startswith("2017-09-01"):
                    print("   ✅ 数据库结束日期更新正确")
                else:
                    print("   ❌ 数据库结束日期更新失败")
                    return False
                    
            else:
                print(f"   获取状态详情失败: {result.get('message')}")
                return False
        else:
            print(f"   获取状态详情失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   验证异常: {e}")
        return False
    
    # 4. 检查历史记录
    print(f"\n4. 检查历史记录...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/backtest-status/{status_id}/history")
        if response.status_code == 200:
            history_list = response.json()  # 直接返回数组
            print(f"   找到 {len(history_list)} 条历史记录")
            
            if history_list:
                latest_history = history_list[0]  # 最新的历史记录
                print(f"   最新历史记录:")
                print(f"     - 操作类型: {latest_history.get('operation_type')}")
                print(f"     - 结束日期: {latest_history.get('end_date')}")
                print(f"     - 创建时间: {latest_history.get('created_at')}")
                
                if latest_history.get('operation_type') == 'update':
                    print("   ✅ 历史记录创建正确")
                else:
                    print("   ❌ 历史记录操作类型错误")
                    return False
                    
                # 处理ISO格式的日期比较
                if latest_history.get('end_date', '').startswith("2017-09-01"):
                    print("   ✅ 历史记录结束日期正确")
                else:
                    print("   ❌ 历史记录结束日期错误")
                    return False
                    
        else:
            print(f"   获取历史记录失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   检查历史记录异常: {e}")
        return False
    
    print(f"\n✅ 前端参数匹配测试全部通过!")
    return True

def test_mixed_params_update():
    """测试混合参数更新（既有前端参数又有后端参数）"""
    print("\n" + "=" * 60)
    print("测试混合参数更新功能")
    print("=" * 60)
    
    # 获取回测状态列表
    try:
        response = requests.get(f"{API_BASE_URL}/api/backtest-status/list")
        if response.status_code == 200:
            backtest_list = response.json()
            if not backtest_list:
                print("没有找到回测状态，跳过混合参数测试")
                return True
                
            test_status = backtest_list[0]
            status_id = test_status['id']
            original_name = test_status['name']
            
            print(f"使用回测状态: ID={status_id}, 名称={original_name}")
            
        else:
            print(f"获取回测列表失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"获取回测列表异常: {e}")
        return False
    
    # 使用混合参数进行更新
    print(f"\n使用混合参数更新回测状态 {status_id}...")
    
    # 混合参数：既有前端参数又有后端参数
    update_data = {
        "new_name": f"{original_name}_混合更新",
        "update_to_date": "2018-01-01",  # 前端参数
        "initial_capital": 150000,       # 后端参数
        "reason": "混合参数测试"          # 后端参数
    }
    
    print(f"混合更新参数: {json.dumps(update_data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/backtest-status/{status_id}/update",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"混合更新成功!")
            
            data = result.get('data', {})
            print(f"新回测名称: {data.get('new_backtest_name')}")
            print(f"更新范围: {data.get('update_range')}")
            
            # 验证混合参数更新
            if data.get('new_backtest_name') == f"{original_name}_混合更新":
                print("✅ 混合参数名称更新正确")
            else:
                print("❌ 混合参数名称更新失败")
                return False
                
            update_range = data.get('update_range', {})
            if update_range.get('end_date') == "2018-01-01":
                print("✅ 混合参数结束日期更新正确")
            else:
                print("❌ 混合参数结束日期更新失败")
                return False
                
        else:
            print(f"混合更新失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"混合更新异常: {e}")
        return False
    
    print(f"\n✅ 混合参数更新测试通过!")
    return True

if __name__ == "__main__":
    print("开始测试前端参数匹配功能...")
    
    # 测试前端参数更新
    success1 = test_frontend_params_update()
    
    # 测试混合参数更新
    success2 = test_mixed_params_update()
    
    if success1 and success2:
        print("\n🎉 所有测试通过！前端参数匹配功能正常工作。")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查实现。")
        sys.exit(1)
