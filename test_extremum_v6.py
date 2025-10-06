#!/usr/bin/env python3
"""
测试极大极小值策略v6的回测功能
验证除零错误是否已经修复
"""

import sys
import os
import requests
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置
API_BASE_URL = "http://localhost:8000"

def test_extremum_v6_backtest():
    """测试极大极小值策略v6回测"""
    print("=" * 60)
    print("测试极大极小值策略v6回测")
    print("=" * 60)
    
    # 使用策略回测API运行回测
    print("\n1. 运行极大极小值策略v6回测...")
    
    backtest_data = {
        "strategy_id": 8,  # 极大极小值策略v6
        "symbol": "TSLA",
        "start_date": "2018-10-06",
        "end_date": "2025-10-06",
        "initial_capital": 100000,
        "parameters": {
            "positionConfig": {
                "mode": "fixed",
                "defaultSize": 0.5
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
                print(f"  - 总收益率: {data.get('total_return', 0) * 100:.2f}%")
                print(f"  - 年化收益率: {data.get('annual_return', 0) * 100:.2f}%")
                print(f"  - 最大回撤: {data.get('max_drawdown', 0) * 100:.2f}%")
                print(f"  - 夏普比率: {data.get('sharpe_ratio', 0):.3f}")
                print(f"  - 胜率: {data.get('win_rate', 0) * 100:.2f}%")
                print(f"  - 盈亏比: {data.get('profit_factor', 0):.3f}")
                
                # 检查权益曲线
                equity_curve = data.get('equity_curve', [])
                print(f"  - 权益曲线数据量: {len(equity_curve)}")
                
                # 检查交易记录
                trades = data.get('trades', [])
                print(f"  - 交易记录数量: {len(trades)}")
                
                if equity_curve:
                    print(f"  ✅ 权益曲线有数据")
                else:
                    print(f"  ❌ 权益曲线无数据")
                    
                if trades:
                    print(f"  ✅ 交易记录有数据")
                    # 显示前几笔交易
                    print(f"  - 前3笔交易:")
                    for i, trade in enumerate(trades[:3]):
                        print(f"    {i+1}. {trade.get('date')} {trade.get('action')} {trade.get('shares')}股 @{trade.get('price'):.2f}")
                else:
                    print(f"  ❌ 交易记录无数据")
                
                return True
            else:
                print(f"❌ 回测结果数据为空")
                return False
        else:
            print(f"❌ 回测失败: HTTP {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 回测过程中发生错误: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 极大极小值策略v6回测测试工具")
    print("=" * 80)
    
    success = test_extremum_v6_backtest()
    
    if success:
        print("\n🎉 极大极小值策略v6回测测试通过！除零错误已修复。")
        sys.exit(0)
    else:
        print("\n❌ 极大极小值策略v6回测测试失败。")
        sys.exit(1)

if __name__ == "__main__":
    main()