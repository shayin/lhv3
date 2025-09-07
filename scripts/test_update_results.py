#!/usr/bin/env python3
"""
测试回测更新结果保存问题
验证更新回测后性能指标和权益曲线是否正确保存
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

def test_update_results():
    """测试更新回测结果保存"""
    print("=" * 60)
    print("测试回测更新结果保存问题")
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
                
            # 选择第一个有合理日期范围的回测状态进行测试
            test_status = None
            for status in backtest_list:
                start_date = status.get('start_date', '')
                end_date = status.get('end_date', '')
                # 检查日期范围是否合理（开始日期早于结束日期）
                if start_date and end_date and start_date < end_date:
                    test_status = status
                    break
            
            if not test_status:
                print("   没有找到日期范围合理的回测状态")
                return False
                
            status_id = test_status['id']
            original_name = test_status['name']
            
            print(f"   选择回测状态: ID={status_id}, 名称={original_name}")
            
        else:
            print(f"   获取回测列表失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   获取回测列表异常: {e}")
        return False
    
    # 2. 检查更新前的状态
    print(f"\n2. 检查更新前的状态...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/backtest-status/{status_id}")
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                status_data = result.get('data', {})
                print(f"   更新前性能指标: {status_data.get('performance_metrics')}")
                print(f"   更新前权益曲线: {'有数据' if status_data.get('equity_curve') else '无数据'}")
                print(f"   更新前交易记录: {'有数据' if status_data.get('trade_records') else '无数据'}")
            else:
                print(f"   获取状态详情失败: {result.get('message')}")
                return False
        else:
            print(f"   获取状态详情失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   检查更新前状态异常: {e}")
        return False
    
    # 3. 执行更新操作
    print(f"\n3. 执行更新操作...")
    
    update_data = {
        "new_name": f"{original_name}_结果测试",
        "update_to_date": "2023-09-01"  # 使用一个合理的结束日期
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
            
        else:
            print(f"   更新失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"   更新异常: {e}")
        return False
    
    # 4. 检查更新后的状态
    print(f"\n4. 检查更新后的状态...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/backtest-status/{status_id}")
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                status_data = result.get('data', {})
                print(f"   更新后性能指标: {status_data.get('performance_metrics')}")
                print(f"   更新后权益曲线: {'有数据' if status_data.get('equity_curve') else '无数据'}")
                print(f"   更新后交易记录: {'有数据' if status_data.get('trade_records') else '无数据'}")
                
                # 检查性能指标是否为空
                performance_metrics = status_data.get('performance_metrics', {})
                if performance_metrics and any(v is not None for v in performance_metrics.values()):
                    print("   ✅ 性能指标有数据")
                else:
                    print("   ❌ 性能指标为空")
                    return False
                    
                # 检查权益曲线是否有数据
                equity_curve = status_data.get('equity_curve')
                if equity_curve and len(equity_curve) > 0:
                    print("   ✅ 权益曲线有数据")
                else:
                    print("   ❌ 权益曲线为空")
                    return False
                    
                # 检查交易记录是否有数据
                trade_records = status_data.get('trade_records')
                if trade_records and len(trade_records) > 0:
                    print("   ✅ 交易记录有数据")
                else:
                    print("   ❌ 交易记录为空")
                    return False
                    
            else:
                print(f"   获取状态详情失败: {result.get('message')}")
                return False
        else:
            print(f"   获取状态详情失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   检查更新后状态异常: {e}")
        return False
    
    # 5. 检查历史记录
    print(f"\n5. 检查历史记录...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/backtest-status/{status_id}/history")
        if response.status_code == 200:
            history_list = response.json()
            print(f"   找到 {len(history_list)} 条历史记录")
            
            if history_list:
                latest_history = history_list[0]  # 最新的历史记录
                print(f"   最新历史记录:")
                print(f"     - 操作类型: {latest_history.get('operation_type')}")
                print(f"     - 性能指标: {latest_history.get('performance_metrics')}")
                print(f"     - 权益曲线: {'有数据' if latest_history.get('equity_curve') else '无数据'}")
                print(f"     - 交易记录: {'有数据' if latest_history.get('trade_records') else '无数据'}")
                
                # 检查历史记录中的性能指标
                history_performance = latest_history.get('performance_metrics', {})
                if history_performance and any(v is not None for v in history_performance.values()):
                    print("   ✅ 历史记录性能指标有数据")
                else:
                    print("   ❌ 历史记录性能指标为空")
                    return False
                    
        else:
            print(f"   获取历史记录失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   检查历史记录异常: {e}")
        return False
    
    print(f"\n✅ 回测更新结果保存测试通过!")
    return True

if __name__ == "__main__":
    print("开始测试回测更新结果保存问题...")
    
    success = test_update_results()
    
    if success:
        print("\n🎉 测试通过！回测更新结果保存正常。")
        sys.exit(0)
    else:
        print("\n❌ 测试失败，回测更新结果保存有问题。")
        sys.exit(1)
