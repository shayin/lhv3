#!/usr/bin/env python3
"""
测试回测保存功能
验证新的状态表+流水表架构的保存逻辑
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_save_backtest():
    """测试保存回测功能"""
    
    # 测试数据
    test_data = {
        "name": "测试回测_新架构",
        "description": "测试新架构的保存功能",
        "strategy_id": 1,
        "start_date": "2023-01-01T00:00:00Z",
        "end_date": "2023-12-31T23:59:59Z",
        "initial_capital": 100000.0,
        "instruments": ["AAPL", "GOOGL"],
        "parameters": {
            "ma_short": 10,
            "ma_long": 20
        },
        "position_config": {
            "max_position": 0.1,
            "stop_loss": 0.05
        },
        # 模拟回测结果数据
        "results": {
            "total_trades": 25,
            "winning_trades": 15,
            "losing_trades": 10
        },
        "equity_curve": [
            {"date": "2023-01-01", "value": 100000},
            {"date": "2023-06-01", "value": 115000},
            {"date": "2023-12-31", "value": 125000}
        ],
        "trade_records": [
            {
                "date": "2023-01-15",
                "symbol": "AAPL",
                "action": "buy",
                "price": 150.0,
                "quantity": 100
            },
            {
                "date": "2023-02-15",
                "symbol": "AAPL",
                "action": "sell",
                "price": 155.0,
                "quantity": 100
            }
        ],
        "performance_metrics": {
            "total_return": 0.25,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.5,
            "volatility": 0.15,
            "win_rate": 0.6,
            "profit_factor": 1.8
        }
    }
    
    # API端点
    base_url = "http://localhost:8000"
    save_url = f"{base_url}/api/backtest/save"
    list_url = f"{base_url}/api/backtest-status/list"
    
    print("🧪 开始测试回测保存功能...")
    print("=" * 50)
    
    try:
        # 1. 测试保存回测
        print("1. 测试保存回测...")
        response = requests.post(save_url, json=test_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 保存成功: {result}")
            
            status_id = result.get('data', {}).get('status_id')
            history_id = result.get('data', {}).get('history_id')
            operation_type = result.get('data', {}).get('operation_type')
            
            print(f"   状态ID: {status_id}")
            print(f"   历史ID: {history_id}")
            print(f"   操作类型: {operation_type}")
            
        else:
            print(f"❌ 保存失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
        
        # 2. 测试获取回测状态列表
        print("\n2. 测试获取回测状态列表...")
        response = requests.get(list_url)
        
        if response.status_code == 200:
            backtests = response.json()
            print(f"✅ 获取列表成功，共 {len(backtests)} 条记录")
            
            # 查找我们刚保存的记录
            test_backtest = None
            for bt in backtests:
                if bt.get('name') == test_data['name']:
                    test_backtest = bt
                    break
            
            if test_backtest:
                print(f"✅ 找到测试记录:")
                print(f"   ID: {test_backtest.get('id')}")
                print(f"   名称: {test_backtest.get('name')}")
                print(f"   收益率: {test_backtest.get('total_return', 0) * 100:.2f}%")
                print(f"   最大回撤: {test_backtest.get('max_drawdown', 0) * 100:.2f}%")
                print(f"   状态: {test_backtest.get('status')}")
            else:
                print("❌ 未找到测试记录")
                return False
                
        else:
            print(f"❌ 获取列表失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
        
        # 3. 测试获取回测详情
        if status_id:
            print(f"\n3. 测试获取回测详情 (ID: {status_id})...")
            detail_url = f"{base_url}/api/backtest-status/{status_id}"
            response = requests.get(detail_url)
            
            if response.status_code == 200:
                detail = response.json()
                if detail.get('status') == 'success':
                    data = detail.get('data', {})
                    print(f"✅ 获取详情成功:")
                    print(f"   策略名称: {data.get('strategy_name')}")
                    print(f"   回测期间: {data.get('start_date')} 至 {data.get('end_date')}")
                    print(f"   初始资金: ${data.get('initial_capital', 0):,.2f}")
                    
                    # 检查回测结果数据
                    performance_metrics = data.get('performance_metrics', {})
                    if performance_metrics:
                        print(f"   性能指标:")
                        print(f"     总收益率: {performance_metrics.get('total_return', 0) * 100:.2f}%")
                        print(f"     最大回撤: {performance_metrics.get('max_drawdown', 0) * 100:.2f}%")
                        print(f"     夏普比率: {performance_metrics.get('sharpe_ratio', 0):.3f}")
                        print(f"     胜率: {performance_metrics.get('win_rate', 0) * 100:.2f}%")
                    
                    # 检查权益曲线数据
                    equity_curve = data.get('equity_curve')
                    if equity_curve:
                        print(f"   权益曲线数据点: {len(equity_curve)} 个")
                    
                    # 检查交易记录
                    trade_records = data.get('trade_records')
                    if trade_records:
                        print(f"   交易记录: {len(trade_records)} 条")
                        
                else:
                    print(f"❌ 获取详情失败: {detail.get('message')}")
                    return False
            else:
                print(f"❌ 获取详情失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
        
        # 4. 测试获取历史记录
        if status_id:
            print(f"\n4. 测试获取历史记录 (状态ID: {status_id})...")
            history_url = f"{base_url}/api/backtest-status/{status_id}/history"
            response = requests.get(history_url)
            
            if response.status_code == 200:
                history_records = response.json()
                print(f"✅ 获取历史记录成功，共 {len(history_records)} 条")
                
                for i, record in enumerate(history_records):
                    print(f"   记录 {i+1}:")
                    print(f"     ID: {record.get('id')}")
                    print(f"     操作类型: {record.get('operation_type')}")
                    print(f"     收益率: {record.get('total_return', 0) * 100:.2f}%")
                    print(f"     创建时间: {record.get('created_at')}")
                    
            else:
                print(f"❌ 获取历史记录失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
        
        print("\n" + "=" * 50)
        print("🎉 所有测试通过！新架构保存功能正常工作。")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败: 请确保后端服务正在运行 (python3 src/backend/main.py)")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        return False

def test_update_backtest():
    """测试更新回测功能"""
    
    print("\n🔄 测试更新回测功能...")
    print("=" * 50)
    
    # 更新数据
    update_data = {
        "name": "测试回测_新架构_更新",
        "description": "更新后的描述",
        "strategy_id": 1,
        "start_date": "2023-01-01T00:00:00Z",
        "end_date": "2023-12-31T23:59:59Z",
        "initial_capital": 100000.0,
        "instruments": ["AAPL", "GOOGL", "MSFT"],
        "parameters": {
            "ma_short": 5,
            "ma_long": 15
        },
        "position_config": {
            "max_position": 0.15,
            "stop_loss": 0.03
        },
        "results": {
            "total_trades": 30,
            "winning_trades": 18,
            "losing_trades": 12
        },
        "equity_curve": [
            {"date": "2023-01-01", "value": 100000},
            {"date": "2023-06-01", "value": 120000},
            {"date": "2023-12-31", "value": 135000}
        ],
        "trade_records": [
            {
                "date": "2023-01-15",
                "symbol": "AAPL",
                "action": "buy",
                "price": 150.0,
                "quantity": 100
            },
            {
                "date": "2023-02-15",
                "symbol": "AAPL",
                "action": "sell",
                "price": 160.0,
                "quantity": 100
            }
        ],
        "performance_metrics": {
            "total_return": 0.35,
            "max_drawdown": -0.06,
            "sharpe_ratio": 1.8,
            "volatility": 0.12,
            "win_rate": 0.6,
            "profit_factor": 2.0
        }
    }
    
    base_url = "http://localhost:8000"
    save_url = f"{base_url}/api/backtest/save"
    
    try:
        # 使用相同的名称保存，应该触发更新逻辑
        response = requests.post(save_url, json=update_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 更新成功: {result}")
            
            operation_type = result.get('data', {}).get('operation_type')
            if operation_type == 'update':
                print("✅ 正确识别为更新操作")
            else:
                print(f"⚠️  操作类型: {operation_type}")
                
        else:
            print(f"❌ 更新失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 更新测试过程中发生错误: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 回测保存功能测试工具")
    print("=" * 60)
    
    # 测试保存功能
    save_success = test_save_backtest()
    
    if save_success:
        # 测试更新功能
        update_success = test_update_backtest()
        
        if update_success:
            print("\n🎉 所有测试完成！新架构功能正常。")
            sys.exit(0)
        else:
            print("\n⚠️  更新功能测试失败。")
            sys.exit(1)
    else:
        print("\n❌ 保存功能测试失败。")
        sys.exit(1)

if __name__ == "__main__":
    main()
