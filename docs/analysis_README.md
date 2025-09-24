# 数据抓取系统

这是一个统一的股票数据抓取系统，支持从多个数据源获取A股和美股的历史K线数据。

## 功能特性

- 🌍 **多数据源支持**：Yahoo Finance、AkShare、Tushare
- 📈 **多市场覆盖**：A股、美股、港股等
- 🔄 **统一数据格式**：标准化的CSV输出格式
- 📁 **自动文件管理**：按数据源和日期分类存储
- 🔍 **股票搜索**：支持代码和名称搜索
- ⚡ **批量抓取**：支持批量获取多只股票数据
- 🛡️ **错误处理**：完善的异常处理和日志记录

## 支持的数据源

### 1. AkShare（推荐）
- **A股数据**：支持沪深两市所有股票
- **美股数据**：支持纳斯达克、纽交所等主要美股
- **中概股**：支持在美上市的中国公司股票
- **数据质量**：高质量的实时数据
- **使用限制**：免费使用，有一定的访问频率限制

### 2. Yahoo Finance
- **美股数据**：全面的美股市场数据
- **国际市场**：支持全球主要股票市场
- **数据历史**：长期历史数据
- **使用限制**：免费使用，可能有访问频率限制

### 3. Tushare
- **A股数据**：专业的A股数据服务
- **基本面数据**：财务数据、公司信息等
- **使用限制**：需要注册获取token，有积分限制

## 数据格式

所有数据源的输出都统一为以下格式：

```csv
date,open,high,low,close,volume,adj_close
2024-04-01,170.03,171.25,169.48,170.03,46240500,170.03
2024-04-02,168.84,169.34,168.23,168.84,49329481,168.84
```

字段说明：
- `date`: 交易日期 (YYYY-MM-DD)
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量
- `adj_close`: 调整后收盘价

## 文件存储结构

数据会自动保存到项目根目录下的 `data/raw/` 文件夹中，按照以下结构组织：

```
data/raw/
├── akshare/
│   └── 20250529/
│       ├── 600519.csv    # A股：贵州茅台
│       ├── AAPL.csv      # 美股：苹果公司
│       └── BABA.csv      # 中概股：阿里巴巴
├── yahoo/
│   └── 20250529/
│       └── AAPL.csv
└── tushare/
    └── 20250529/
        └── 600519.csv
```

**注意**：无论从哪个目录执行脚本，数据都会保存到项目根目录下的 `data/raw/` 文件夹中，不会在当前执行目录下创建文件。

## 快速开始

### 1. 安装依赖

```bash
pip install akshare yfinance tushare pandas
```

### 2. 基本使用

```python
from src.analysis.data_manager import DataManager

# 初始化数据管理器
manager = DataManager()

# 抓取A股数据
file_path = manager.fetch_stock_data('akshare', '600519', 
                                   start_date='2024-01-01', 
                                   end_date='2024-12-31')

# 抓取美股数据
file_path = manager.fetch_stock_data('akshare', 'AAPL', 
                                   start_date='2024-01-01', 
                                   end_date='2024-12-31')

# 抓取中概股数据
file_path = manager.fetch_stock_data('akshare', 'BABA', 
                                   start_date='2024-01-01', 
                                   end_date='2024-12-31')
```

### 3. 批量抓取

```python
# 批量抓取多只股票（A股+美股）
symbols = ['600519', 'AAPL', 'TSLA', '000858', 'MSFT']
results = manager.batch_fetch('akshare', symbols, 
                            start_date='2024-01-01', 
                            end_date='2024-12-31')

for symbol, file_path in results.items():
    if file_path:
        print(f"✅ {symbol}: {file_path}")
    else:
        print(f"❌ {symbol}: 抓取失败")
```

### 4. 股票搜索

```python
# 搜索A股
a_stocks = manager.search_stocks('akshare', '茅台')

# 搜索美股
us_stocks = manager.search_stocks('akshare', 'Apple')

# 获取股票列表
stock_list = manager.get_stock_list('akshare')
```

## AkShare美股支持详情

AkShare数据源现已全面支持美股数据抓取：

### 支持的美股类型
- **主板美股**：AAPL、MSFT、GOOGL、AMZN等
- **中概股**：BABA、JD、PDD、BIDU等
- **新能源车**：TSLA、NIO、XPEV、LI等
- **科技股**：META、NVDA、NFLX等

### 使用示例

```python
from src.analysis.data_manager import DataManager

manager = DataManager()

# 抓取苹果公司数据
apple_data = manager.fetch_stock_data('akshare', 'AAPL', 
                                    start_date='2024-01-01', 
                                    end_date='2024-12-31')

# 抓取特斯拉数据
tesla_data = manager.fetch_stock_data('akshare', 'TSLA', 
                                    start_date='2024-01-01', 
                                    end_date='2024-12-31')

# 抓取阿里巴巴数据
baba_data = manager.fetch_stock_data('akshare', 'BABA', 
                                   start_date='2024-01-01', 
                                   end_date='2024-12-31')
```

### 股票代码识别
系统会自动识别股票代码类型：
- **A股代码**：6位数字（如：600519）
- **美股代码**：字母组合（如：AAPL、TSLA）

### 常用美股列表
系统内置了20只常用美股：
- AAPL (Apple Inc.)
- MSFT (Microsoft Corporation)
- GOOGL (Alphabet Inc.)
- AMZN (Amazon.com Inc.)
- TSLA (Tesla Inc.)
- META (Meta Platforms Inc.)
- NVDA (NVIDIA Corporation)
- NFLX (Netflix Inc.)
- BABA (Alibaba Group Holding Limited)
- JD (JD.com Inc.)
- 等等...

## 运行示例

```bash
# 运行完整示例
python src/analysis/examples/fetch_data_example.py
```

示例将演示：
1. A股数据抓取（贵州茅台）
2. 美股数据抓取（苹果公司）
3. 中概股数据抓取（阿里巴巴）
4. 股票搜索功能
5. 批量数据抓取
6. 按市场分类的股票列表

## 注意事项

1. **网络连接**：确保网络连接稳定
2. **访问频率**：避免过于频繁的请求，建议间隔1-2秒
3. **数据质量**：不同数据源的数据质量和更新频率可能不同
4. **存储空间**：长期历史数据可能占用较大存储空间
5. **合规使用**：请遵守各数据源的使用条款

## 错误处理

系统具有完善的错误处理机制：
- 网络连接错误自动重试
- 数据格式异常自动处理
- 详细的日志记录便于调试
- 优雅的错误降级处理

## 扩展开发

如需添加新的数据源，请：
1. 继承 `DataFetcher` 基类
2. 实现必要的抽象方法
3. 在 `DataManager` 中注册新数据源

## 许可证

本项目采用 MIT 许可证。 