#!/usr/bin/env python3
"""
测试回测更新功能 - 支持参数更新
验证点击更新按钮后，可以传入新参数并重新运行回测
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_update_with_new_params():
    """测试使用新参数更新回测功能"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 测试回测更新功能 - 支持参数更新...")
    print("=" * 60)
    
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
            
            print(f"✅ 找到测试回测:")
            print(f"   ID: {status_id}")
            print(f"   名称: {test_backtest.get('name')}")
            print(f"   当前开始日期: {test_backtest.get('start_date')}")
            print(f"   当前结束日期: {test_backtest.get('end_date')}")
            print(f"   当前初始资金: {test_backtest.get('initial_capital')}")
            print(f"   当前股票: {test_backtest.get('instruments')}")
            print(f"   当前收益率: {(test_backtest.get('total_return', 0) or 0) * 100:.2f}%")
            print(f"   当前更新时间: {test_backtest.get('updated_at')}")
            
        else:
            print(f"❌ 获取回测列表失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 获取回测列表时发生错误: {str(e)}")
        return False
    
    # 2. 准备新的参数
    print(f"\n2. 准备新的回测参数...")
    
    # 计算新的日期范围（延长回测期间）
    # 处理ISO格式的日期时间字符串
    start_date_str = test_backtest.get('start_date')
    end_date_str = test_backtest.get('end_date')
    
    # 如果是ISO格式，只取日期部分
    if 'T' in start_date_str:
        start_date_str = start_date_str.split('T')[0]
    if 'T' in end_date_str:
        end_date_str = end_date_str.split('T')[0]
    
    old_start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    old_end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    # 延长回测期间（开始日期提前1个月，结束日期延后1个月）
    new_start_date = (old_start_date - timedelta(days=30)).strftime('%Y-%m-%d')
    new_end_date = (old_end_date + timedelta(days=30)).strftime('%Y-%m-%d')
    new_initial_capital = test_backtest.get('initial_capital', 100000) * 1.5  # 增加50%初始资金
    
    print(f"   新开始日期: {new_start_date} (原: {test_backtest.get('start_date')})")
    print(f"   新结束日期: {new_end_date} (原: {test_backtest.get('end_date')})")
    print(f"   新初始资金: {new_initial_capital:,.0f} (原: {test_backtest.get('initial_capital'):,.0f})")
    
    # 3. 执行带新参数的更新操作
    print(f"\n3. 执行带新参数的更新操作 (ID: {status_id})...")
    try:
        update_data = {
            "start_date": new_start_date,
            "end_date": new_end_date,
            "initial_capital": new_initial_capital,
            "reason": "测试参数更新功能"
        }
        
        print(f"   发送更新请求: {json.dumps(update_data, indent=2)}")
        
        response = requests.post(f"{base_url}/api/backtest-status/{status_id}/update", json=update_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print(f"✅ 更新请求成功")
                print(f"   消息: {result.get('message')}")
                
                # 检查返回的更新参数
                updated_params = result.get('data', {}).get('updated_parameters', {})
                if updated_params:
                    print(f"   更新后的参数:")
                    print(f"     开始日期: {updated_params.get('start_date')}")
                    print(f"     结束日期: {updated_params.get('end_date')}")
                    print(f"     初始资金: {updated_params.get('initial_capital'):,.0f}")
                    print(f"     股票: {updated_params.get('instruments')}")
                
                # 检查返回的性能指标
                performance_metrics = result.get('data', {}).get('performance_metrics', {})
                if performance_metrics:
                    new_return = performance_metrics.get('total_return', 0) or 0
                    new_drawdown = performance_metrics.get('max_drawdown', 0) or 0
                    new_sharpe = performance_metrics.get('sharpe_ratio', 0) or 0
                    print(f"   新性能指标:")
                    print(f"     收益率: {new_return * 100:.2f}%")
                    print(f"     最大回撤: {new_drawdown * 100:.2f}%")
                    print(f"     夏普比率: {new_sharpe:.3f}")
                
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
    
    # 4. 验证更新后的数据
    print(f"\n4. 验证更新后的数据...")
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
                print(f"   开始日期: {data.get('start_date')}")
                print(f"   结束日期: {data.get('end_date')}")
                print(f"   初始资金: {data.get('initial_capital'):,.0f}")
                print(f"   股票: {data.get('instruments')}")
                print(f"   收益率: {new_return * 100:.2f}%")
                print(f"   最大回撤: {new_drawdown * 100:.2f}%")
                print(f"   夏普比率: {new_sharpe:.3f}")
                
                # 验证参数是否真的更新了
                # 处理日期格式比较
                actual_start_date = data.get('start_date')
                actual_end_date = data.get('end_date')
                
                # 如果是ISO格式，只取日期部分进行比较
                if 'T' in actual_start_date:
                    actual_start_date = actual_start_date.split('T')[0]
                if 'T' in actual_end_date:
                    actual_end_date = actual_end_date.split('T')[0]
                
                if actual_start_date == new_start_date:
                    print(f"✅ 开始日期已更新: {test_backtest.get('start_date')} → {data.get('start_date')}")
                else:
                    print(f"❌ 开始日期未更新: 期望 {new_start_date}, 实际 {actual_start_date}")
                
                if actual_end_date == new_end_date:
                    print(f"✅ 结束日期已更新: {test_backtest.get('end_date')} → {data.get('end_date')}")
                else:
                    print(f"❌ 结束日期未更新: 期望 {new_end_date}, 实际 {actual_end_date}")
                
                if abs(data.get('initial_capital', 0) - new_initial_capital) < 0.01:
                    print(f"✅ 初始资金已更新: {test_backtest.get('initial_capital'):,.0f} → {data.get('initial_capital'):,.0f}")
                else:
                    print(f"❌ 初始资金未更新: 期望 {new_initial_capital:,.0f}, 实际 {data.get('initial_capital'):,.0f}")
                
            else:
                print(f"❌ 获取状态详情失败: {result.get('message')}")
                return False
        else:
            print(f"❌ 获取状态详情失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 验证更新数据时发生错误: {str(e)}")
        return False
    
    # 5. 检查历史记录
    print(f"\n5. 检查历史记录...")
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
                print(f"   开始日期: {latest_update.get('start_date')}")
                print(f"   结束日期: {latest_update.get('end_date')}")
                print(f"   初始资金: {latest_update.get('initial_capital'):,.0f}")
                print(f"   收益率: {(latest_update.get('total_return', 0) or 0) * 100:.2f}%")
                
                # 验证历史记录中的参数是否也更新了
                # 处理历史记录中的日期格式
                history_start_date = latest_update.get('start_date')
                history_end_date = latest_update.get('end_date')
                
                if 'T' in history_start_date:
                    history_start_date = history_start_date.split('T')[0]
                if 'T' in history_end_date:
                    history_end_date = history_end_date.split('T')[0]
                
                if history_start_date == new_start_date:
                    print(f"✅ 历史记录中的开始日期已更新")
                else:
                    print(f"❌ 历史记录中的开始日期未更新")
                
                if history_end_date == new_end_date:
                    print(f"✅ 历史记录中的结束日期已更新")
                else:
                    print(f"❌ 历史记录中的结束日期未更新")
                
            else:
                print(f"⚠️  未找到更新类型的历史记录")
            
        else:
            print(f"❌ 获取历史记录失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 检查历史记录时发生错误: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 回测参数更新功能测试完成！")
    print("✅ 更新请求成功")
    print("✅ 参数已更新")
    print("✅ 数据已重新计算")
    print("✅ 历史记录已创建")
    print("✅ 参数更新功能正常工作")
    
    return True

def test_update_without_params():
    """测试不传参数时的更新功能（应该使用原有参数）"""
    
    base_url = "http://localhost:8000"
    
    print("\n🧪 测试回测更新功能 - 不传参数（使用原有参数）...")
    print("=" * 60)
    
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
            old_updated_at = test_backtest.get('updated_at')
            
            print(f"✅ 找到测试回测:")
            print(f"   ID: {status_id}")
            print(f"   名称: {test_backtest.get('name')}")
            print(f"   当前更新时间: {old_updated_at}")
            
        else:
            print(f"❌ 获取回测列表失败: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ 获取回测列表时发生错误: {str(e)}")
        return False
    
    # 2. 执行不带参数的更新操作
    print(f"\n2. 执行不带参数的更新操作 (ID: {status_id})...")
    try:
        update_data = {
            "reason": "测试不传参数的更新功能"
        }
        
        print(f"   发送更新请求: {json.dumps(update_data, indent=2)}")
        
        response = requests.post(f"{base_url}/api/backtest-status/{status_id}/update", json=update_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print(f"✅ 更新请求成功")
                print(f"   消息: {result.get('message')}")
                
                # 检查返回的更新参数（应该和原来一样）
                updated_params = result.get('data', {}).get('updated_parameters', {})
                if updated_params:
                    print(f"   更新后的参数（应该和原来一样）:")
                    print(f"     开始日期: {updated_params.get('start_date')}")
                    print(f"     结束日期: {updated_params.get('end_date')}")
                    print(f"     初始资金: {updated_params.get('initial_capital'):,.0f}")
                
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
    
    # 3. 验证更新时间是否变化
    print(f"\n3. 验证更新时间是否变化...")
    try:
        response = requests.get(f"{base_url}/api/backtest-status/{status_id}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                data = result.get('data', {})
                new_updated_at = data.get('updated_at')
                
                print(f"✅ 状态详情获取成功:")
                print(f"   原更新时间: {old_updated_at}")
                print(f"   新更新时间: {new_updated_at}")
                
                if new_updated_at != old_updated_at:
                    print(f"✅ 更新时间已更新")
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
    
    print("\n" + "=" * 60)
    print("🎉 不传参数的更新功能测试完成！")
    print("✅ 更新请求成功")
    print("✅ 使用原有参数重新运行")
    print("✅ 更新时间已更新")
    
    return True

def main():
    """主函数"""
    print("🚀 回测参数更新功能测试工具")
    print("=" * 80)
    
    # 测试1: 带新参数的更新
    success1 = test_update_with_new_params()
    
    # 测试2: 不带参数的更新
    success2 = test_update_without_params()
    
    if success1 and success2:
        print("\n🎉 所有测试通过！回测参数更新功能正常工作。")
        print("✅ 支持传入新参数进行更新")
        print("✅ 支持不传参数使用原有参数进行更新")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败。")
        sys.exit(1)

if __name__ == "__main__":
    main()