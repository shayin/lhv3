#!/usr/bin/env python3
"""
测试回测引擎直接运行
验证回测引擎是否能正确生成权益曲线和性能指标
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

def test_backtest_engine_directly():
    """直接测试回测引擎"""
    print("=" * 60)
    print("直接测试回测引擎")
    print("=" * 60)
    
    # 使用策略回测API直接运行回测
    print("\n1. 直接运行策略回测...")
    
    backtest_data = {
        "strategy_id": 1,  # 使用默认的MA交叉策略
        "symbol": "TSLA",
        "start_date": "2015-07-09",
        "end_date": "2017-09-01",
        "initial_capital": 150000,
        "parameters": {
            "positionConfig": {
                "mode": "fixed",
                "defaultSize": 1.0
            }
        },
        "commission_rate": 0.0015,
        "slippage_rate": 0.001,
        "data_source": "database",
        "features": []
    }
    
    print(f"回测参数: {json.dumps(backtest_data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/strategies/backtest",
            json=backtest_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"回测成功!")
            print(f"响应状态: {result.get('status')}")
            print(f"响应消息: {result.get('message')}")
            
            data = result.get('data', {})
            if data:
                print(f"\n回测结果数据:")
                print(f"  - 总收益率: {data.get('total_return')}")
                print(f"  - 最大回撤: {data.get('max_drawdown')}")
                print(f"  - 夏普比率: {data.get('sharpe_ratio')}")
                print(f"  - 胜率: {data.get('win_rate')}")
                print(f"  - 盈亏比: {data.get('profit_factor')}")
                print(f"  - 权益曲线数据量: {len(data.get('equity_curve', []))}")
                print(f"  - 交易记录数量: {len(data.get('trades', []))}")
                
                # 检查权益曲线
                equity_curve = data.get('equity_curve', [])
                if equity_curve:
                    print(f"  - 权益曲线样本: {equity_curve[:2]}")
                    print("  ✅ 权益曲线有数据")
                else:
                    print("  ❌ 权益曲线为空")
                    
                # 检查交易记录
                trades = data.get('trades', [])
                if trades:
                    print(f"  - 交易记录样本: {trades[:2]}")
                    print("  ✅ 交易记录有数据")
                else:
                    print("  ❌ 交易记录为空")
                    
                # 检查性能指标
                if data.get('total_return') is not None:
                    print("  ✅ 性能指标有数据")
                else:
                    print("  ❌ 性能指标为空")
                    
            else:
                print("  ❌ 回测结果数据为空")
                return False
                
        else:
            print(f"回测失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"回测异常: {e}")
        return False
    
    return True

def test_backtest_service():
    """测试回测服务"""
    print("\n" + "=" * 60)
    print("测试回测服务")
    print("=" * 60)
    
    # 使用回测测试API
    print("\n1. 使用回测测试API...")
    
    backtest_data = {
        "strategy_id": 1,
        "symbol": "TSLA",
        "start_date": "2015-07-09",
        "end_date": "2017-09-01",
        "initial_capital": 150000,
        "parameters": {
            "positionConfig": {
                "mode": "fixed",
                "defaultSize": 1.0
            }
        },
        "data_source": "database",
        "features": []
    }
    
    print(f"回测参数: {json.dumps(backtest_data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/backtest/test",
            json=backtest_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"回测成功!")
            print(f"响应状态: {result.get('status')}")
            print(f"响应消息: {result.get('message')}")
            
            data = result.get('data', {})
            if data:
                print(f"\n回测结果数据:")
                print(f"  - 总收益率: {data.get('total_return')}")
                print(f"  - 最大回撤: {data.get('max_drawdown')}")
                print(f"  - 夏普比率: {data.get('sharpe_ratio')}")
                print(f"  - 胜率: {data.get('win_rate')}")
                print(f"  - 盈亏比: {data.get('profit_factor')}")
                print(f"  - 权益曲线数据量: {len(data.get('equity_curve', []))}")
                print(f"  - 交易记录数量: {len(data.get('trades', []))}")
                
                # 检查权益曲线
                equity_curve = data.get('equity_curve', [])
                if equity_curve:
                    print(f"  - 权益曲线样本: {equity_curve[:2]}")
                    print("  ✅ 权益曲线有数据")
                else:
                    print("  ❌ 权益曲线为空")
                    
                # 检查交易记录
                trades = data.get('trades', [])
                if trades:
                    print(f"  - 交易记录样本: {trades[:2]}")
                    print("  ✅ 交易记录有数据")
                else:
                    print("  ❌ 交易记录为空")
                    
                # 检查性能指标
                if data.get('total_return') is not None:
                    print("  ✅ 性能指标有数据")
                else:
                    print("  ❌ 性能指标为空")
                    
            else:
                print("  ❌ 回测结果数据为空")
                return False
                
        else:
            print(f"回测失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"回测异常: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("开始测试回测引擎...")
    
    # 测试策略回测API
    success1 = test_backtest_engine_directly()
    
    # 测试回测测试API
    success2 = test_backtest_service()
    
    if success1 and success2:
        print("\n🎉 回测引擎测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 回测引擎测试失败。")
        sys.exit(1)
