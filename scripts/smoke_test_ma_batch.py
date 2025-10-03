import pandas as pd
import importlib.util
from importlib.machinery import SourceFileLoader
import os
import sys

# 将项目根目录加入 sys.path，以便策略模块中的绝对导入（src.*）能被解析
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# 为避免导入顶层包触发API应用启动，直接从文件加载策略类
strategy_path = os.path.abspath('src/backend/strategy/templates/ma_crossover_strategy.py')
loader = SourceFileLoader('ma_crossover_strategy', strategy_path)
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
MACrossoverStrategy = getattr(module, 'MACrossoverStrategy')

# 使用合成上升序列以确保产生交叉信号以测试分批逻辑
dates = pd.date_range(start='2020-01-01', periods=50, freq='D')
# 先保持一段高位，然后下跌形成低点，再回升，制造MA上穿情形
prefix = [20]*5
dip = [15,14,13,12,11]
tail_len = 50 - (len(prefix) + len(dip))
tail = list(range(12, 12 + tail_len))
prices = prefix + dip + tail
print('len(dates)=', len(dates))
print('len(prices)=', len(prices))
df = pd.DataFrame({
    'date': dates,
    'open': prices,
    'high': [p + 0.5 for p in prices],
    'low': [p - 0.5 for p in prices],
    'close': prices,
    'volume': [1000] * len(prices),
    'adj_close': prices,
})

# 初始化策略并设置参数
params = {
    'short_window': 3,
    'long_window': 5,
    'batch_count': 3,
    'batch_interval_bars': 2,
    'batch_weights': [0.5, 0.3, 0.2]
}

strategy = MACrossoverStrategy(parameters=params)
strategy.set_data(df)

signals = strategy.generate_signals()
print('Signals columns:', signals.columns.tolist())
# 打印含有买入信号的位置及 position_size
buy_signals = signals[signals['signal'] == 1]
print('Total buy signals (including batches):', len(buy_signals))
print(buy_signals[['date','close','signal','trigger_reason','position_size']].head(20))
