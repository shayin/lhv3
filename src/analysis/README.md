# 数据抓取系统

这是一个统一的股票数据抓取系统，支持多种数据源，可以自动抓取股票K线数据并按规范格式保存。

## 功能特性

- 🌐 **多数据源支持**: Yahoo Finance、AkShare、Tushare
- 📊 **标准化数据格式**: 统一的CSV格式输出
- 📁 **自动文件管理**: 按数据源和日期自动分类存储
- 🔍 **股票搜索**: 支持按代码和名称搜索股票
- 📦 **批量抓取**: 支持批量抓取多只股票数据
- 🎯 **任务管理**: 创建和执行数据抓取任务

## 目录结构

```
src/analysis/
├── __init__.py                 # 包初始化
├── data_fetcher.py            # 数据抓取基类
├── data_manager.py            # 数据管理器
├── data_sources/              # 数据源实现
│   ├── __init__.py
│   ├── yahoo_fetcher.py       # Yahoo Finance数据源
│   ├── akshare_fetcher.py     # AkShare数据源
│   └── tushare_fetcher.py     # Tushare数据源
├── examples/                  # 示例代码
│   └── fetch_data_example.py  # 使用示例
└── README.md                  # 说明文档
```

## 数据存储格式

抓取的数据按以下目录结构存储：

```
data/raw/
├── yahoo/                     # Yahoo Finance数据
│   └── 20250528/             # 抓取日期
│       ├── AAPL.csv          # 苹果股票数据
│       └── MSFT.csv          # 微软股票数据
├── akshare/                   # AkShare数据
│   └── 20250528/
│       ├── 600519.csv        # 贵州茅台数据
│       └── 000001.csv        # 平安银行数据
└── tushare/                   # Tushare数据
    └── 20250528/
        ├── 000001.SZ.csv     # 平安银行数据
        └── 600519.SH.csv     # 贵州茅台数据
```

## CSV数据格式

所有数据源的输出都统一为以下格式：

```csv
date,open,high,low,close,volume,adj_close
2024-01-01,150.00,152.50,149.00,151.20,1000000,151.20
2024-01-02,151.20,153.80,150.50,152.90,1200000,152.90
```

字段说明：
- `date`: 交易日期 (YYYY-MM-DD)
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量
- `adj_close`: 调整后收盘价

## 快速开始

### 1. 安装依赖

```bash
pip install yfinance akshare tushare pandas
```

### 2. 基本使用

```python
from src.analysis.data_manager import DataManager

# 初始化数据管理器
manager = DataManager()

# 抓取单只股票数据
file_path = manager.fetch_stock_data('yahoo', 'AAPL', '2024-01-01', '2024-12-31')
print(f"数据已保存到: {file_path}")

# 批量抓取
symbols = ['AAPL', 'MSFT', 'GOOGL']
results = manager.batch_fetch('yahoo', symbols, '2024-01-01')
```

### 3. 运行示例

```bash
cd src/analysis/examples
python fetch_data_example.py
```

## 数据源配置

### Yahoo Finance
- **支持市场**: 美股、港股等
- **股票代码格式**: AAPL, MSFT, GOOGL
- **无需配置**: 开箱即用

### AkShare
- **支持市场**: A股
- **股票代码格式**: 6位数字 (000001, 600519)
- **无需配置**: 开箱即用

### Tushare
- **支持市场**: A股、港股、美股等
- **股票代码格式**: 000001.SZ, 600519.SH
- **需要配置**: 需要注册获取token

#### Tushare配置方法

1. 访问 [https://tushare.pro/](https://tushare.pro/) 注册账号
2. 获取API token
3. 使用token初始化：

```python
manager = DataManager(tushare_token="your_token_here")
```

## API参考

### DataManager

主要的数据管理类，提供统一的数据抓取接口。

#### 方法

- `get_available_sources()`: 获取可用数据源列表
- `fetch_stock_data(source, symbol, start_date, end_date)`: 抓取单只股票数据
- `batch_fetch(source, symbols, start_date, end_date)`: 批量抓取数据
- `get_stock_list(source)`: 获取股票列表
- `search_stocks(source, query)`: 搜索股票
- `create_fetch_task(source, symbols, start_date, end_date)`: 创建抓取任务
- `execute_task(task)`: 执行抓取任务

### DataFetcher (基类)

所有数据源实现的基类，定义了统一的接口。

#### 抽象方法

- `fetch_stock_data(symbol, start_date, end_date)`: 抓取股票数据
- `get_stock_list()`: 获取股票列表

#### 通用方法

- `save_data(symbol, data)`: 保存数据到文件
- `fetch_and_save(symbol, start_date, end_date)`: 抓取并保存数据
- `batch_fetch(symbols, start_date, end_date)`: 批量抓取
- `load_saved_data(symbol)`: 加载已保存的数据

## 扩展新数据源

要添加新的数据源，需要继承`DataFetcher`基类并实现抽象方法：

```python
from src.analysis.data_fetcher import DataFetcher

class NewDataFetcher(DataFetcher):
    def __init__(self, base_path="data/raw"):
        super().__init__("new_source", base_path)
    
    def fetch_stock_data(self, symbol, start_date=None, end_date=None):
        # 实现数据抓取逻辑
        pass
    
    def get_stock_list(self):
        # 实现股票列表获取逻辑
        pass
```

## 注意事项

1. **网络连接**: 数据抓取需要稳定的网络连接
2. **API限制**: 某些数据源可能有访问频率限制
3. **数据质量**: 不同数据源的数据质量和完整性可能有差异
4. **存储空间**: 批量抓取会占用较多存储空间
5. **合规使用**: 请遵守各数据源的使用条款

## 故障排除

### 常见问题

1. **导入错误**: 确保已安装所需依赖包
2. **网络超时**: 检查网络连接，可能需要重试
3. **数据为空**: 检查股票代码格式是否正确
4. **权限错误**: 确保有写入data目录的权限

### 日志调试

启用详细日志来调试问题：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 许可证

本项目遵循MIT许可证。 