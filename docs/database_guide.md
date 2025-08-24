# SQLite 数据库使用指南

## 概述

本项目使用 SQLite 作为数据库，数据库文件位于 `backtesting.db`。本文档详细说明了数据库的表结构、字段含义以及常用的 SQLite 操作。

## 数据库文件位置

```
/Users/shayin/data1/htdocs/project/joy/lhv3/backtesting.db
```

## 表结构概览

数据库包含以下主要表：

1. **data_sources** - 数据源配置表
2. **stocks** - 股票基本信息表
3. **stock_data** - 股票K线数据表
4. **daily_prices** - 日线价格数据表
5. **strategies** - 策略配置表
6. **backtests** - 回测记录表
7. **trades** - 交易记录表
8. **technical_indicators** - 技术指标表

## 详细表结构

### 1. data_sources 表 - 数据源配置

```sql
CREATE TABLE data_sources (
    id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    api_key VARCHAR(200),
    api_secret VARCHAR(200),
    base_url VARCHAR(200),
    created_at DATETIME,
    PRIMARY KEY (id),
    UNIQUE (name)
);
```

**字段说明：**
- `id`: 主键，数据源唯一标识
- `name`: 数据源名称（如：Yahoo Finance、AkShare、Tushare）
- `description`: 数据源描述
- `api_key`: API密钥
- `api_secret`: API密钥
- `base_url`: 数据源基础URL
- `created_at`: 创建时间

### 2. stocks 表 - 股票基本信息

```sql
CREATE TABLE stocks (
    id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL,
    exchange VARCHAR(20),
    industry VARCHAR(50),
    sector VARCHAR(50),
    source_id INTEGER NOT NULL,
    description TEXT,
    created_at DATETIME,
    last_updated DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT uix_stock_symbol_source UNIQUE (symbol, source_id),
    FOREIGN KEY(source_id) REFERENCES data_sources (id)
);
```

**字段说明：**
- `id`: 主键，股票唯一标识
- `symbol`: 股票代码（如：AAPL、MSFT、000001）
- `name`: 股票名称
- `type`: 股票类型（如：美股、A股、港股）
- `exchange`: 交易所
- `industry`: 行业
- `sector`: 板块
- `source_id`: 数据源ID
- `description`: 描述
- `created_at`: 创建时间
- `last_updated`: 最后更新时间

### 3. stock_data 表 - 股票K线数据

```sql
CREATE TABLE stock_data (
    id INTEGER NOT NULL,
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    adj_close FLOAT,
    turnover FLOAT,
    pe_ratio FLOAT,
    pb_ratio FLOAT,
    dividend_yield FLOAT,
    PRIMARY KEY (id),
    CONSTRAINT uix_stock_date UNIQUE (stock_id, date),
    FOREIGN KEY(stock_id) REFERENCES stocks (id)
);
```

**字段说明：**
- `id`: 主键
- `stock_id`: 股票ID
- `date`: 交易日期
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量
- `adj_close`: 复权收盘价
- `turnover`: 换手率
- `pe_ratio`: 市盈率
- `pb_ratio`: 市净率
- `dividend_yield`: 股息率

### 4. daily_prices 表 - 日线价格数据

```sql
CREATE TABLE daily_prices (
    id INTEGER NOT NULL,
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    adjusted_close FLOAT,
    PRIMARY KEY (id),
    CONSTRAINT uix_stock_date_price UNIQUE (stock_id, date),
    FOREIGN KEY(stock_id) REFERENCES stocks (id)
);
```

**字段说明：**
- `id`: 主键
- `stock_id`: 股票ID
- `date`: 交易日期
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量
- `adjusted_close`: 复权收盘价

### 5. strategies 表 - 策略配置

```sql
CREATE TABLE strategies (
    id INTEGER NOT NULL,
    name VARCHAR,
    description VARCHAR,
    code VARCHAR,
    parameters VARCHAR,
    created_at DATETIME,
    updated_at DATETIME,
    is_template BOOLEAN,
    template VARCHAR,
    PRIMARY KEY (id)
);
```

**字段说明：**
- `id`: 主键
- `name`: 策略名称
- `description`: 策略描述
- `code`: 策略代码
- `parameters`: 策略参数
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `is_template`: 是否为模板
- `template`: 模板名称

### 6. backtests 表 - 回测记录

```sql
CREATE TABLE backtests (
    id INTEGER NOT NULL,
    strategy_id INTEGER,
    name VARCHAR,
    description VARCHAR,
    start_date DATETIME,
    end_date DATETIME,
    initial_capital FLOAT,
    instruments JSON,
    parameters JSON,
    results JSON,
    created_at DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY(strategy_id) REFERENCES strategies (id)
);
```

**字段说明：**
- `id`: 主键
- `strategy_id`: 策略ID
- `name`: 回测名称
- `description`: 回测描述
- `start_date`: 开始日期
- `end_date`: 结束日期
- `initial_capital`: 初始资金
- `instruments`: 交易标的（JSON）
- `parameters`: 参数（JSON）
- `results`: 结果（JSON）
- `created_at`: 创建时间

### 7. trades 表 - 交易记录

```sql
CREATE TABLE trades (
    id INTEGER NOT NULL,
    backtest_id INTEGER,
    datetime DATETIME,
    symbol VARCHAR,
    direction VARCHAR,
    price FLOAT,
    quantity FLOAT,
    commission FLOAT,
    PRIMARY KEY (id),
    FOREIGN KEY(backtest_id) REFERENCES backtests (id)
);
```

**字段说明：**
- `id`: 主键
- `backtest_id`: 回测ID
- `datetime`: 交易时间
- `symbol`: 交易标的
- `direction`: 交易方向（buy/sell）
- `price`: 交易价格
- `quantity`: 交易数量
- `commission`: 手续费

### 8. technical_indicators 表 - 技术指标

```sql
CREATE TABLE technical_indicators (
    id INTEGER NOT NULL,
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,
    indicator_name VARCHAR(50) NOT NULL,
    indicator_value FLOAT NOT NULL,
    parameter VARCHAR(50),
    PRIMARY KEY (id),
    CONSTRAINT uix_stock_indicator UNIQUE (stock_id, date, indicator_name, parameter),
    FOREIGN KEY(stock_id) REFERENCES stocks (id)
);
```

**字段说明：**
- `id`: 主键
- `stock_id`: 股票ID
- `date`: 计算日期
- `indicator_name`: 指标名称
- `indicator_value`: 指标值
- `parameter`: 参数

## SQLite 常用操作

### 1. 连接数据库

```bash
# 在项目根目录下
sqlite3 backtesting.db
```

### 2. 查看数据库信息

```sql
-- 查看所有表
.tables

-- 查看表结构
.schema stocks
.schema stock_data
.schema strategies

-- 查看表的详细信息
PRAGMA table_info(stocks);
PRAGMA table_info(stock_data);
```

### 3. 常用查询语句

#### 查看股票列表
```sql
SELECT id, symbol, name, type, last_updated 
FROM stocks 
ORDER BY symbol;
```

#### 查看某只股票的数据
```sql
SELECT date, open, high, low, close, volume 
FROM stock_data 
WHERE stock_id = 1 
ORDER BY date DESC 
LIMIT 10;
```

#### 查看数据源列表
```sql
SELECT id, name, description, created_at 
FROM data_sources;
```

#### 查看策略列表
```sql
SELECT id, name, description, created_at 
FROM strategies;
```

#### 查看回测记录
```sql
SELECT 
    b.id,
    s.name as strategy_name,
    b.name as backtest_name,
    b.start_date,
    b.end_date,
    b.initial_capital,
    b.created_at
FROM backtests b
LEFT JOIN strategies s ON b.strategy_id = s.id
ORDER BY b.created_at DESC;
```

#### 查看交易记录
```sql
SELECT 
    t.datetime,
    t.symbol,
    t.direction,
    t.price,
    t.quantity,
    t.commission
FROM trades t
WHERE t.backtest_id = 1
ORDER BY t.datetime;
```

### 4. 数据统计查询

#### 统计每只股票的数据条数
```sql
SELECT 
    s.symbol,
    s.name,
    COUNT(sd.id) as data_count,
    MIN(sd.date) as first_date,
    MAX(sd.date) as last_date
FROM stocks s
LEFT JOIN stock_data sd ON s.id = sd.stock_id
GROUP BY s.id, s.symbol, s.name
ORDER BY data_count DESC;
```

#### 查看数据缺失情况
```sql
SELECT 
    s.symbol,
    s.name,
    COUNT(sd.id) as data_count,
    CASE 
        WHEN COUNT(sd.id) = 0 THEN '无数据'
        WHEN COUNT(sd.id) < 100 THEN '数据不足'
        ELSE '数据充足'
    END as status
FROM stocks s
LEFT JOIN stock_data sd ON s.id = sd.stock_id
GROUP BY s.id, s.symbol, s.name;
```

#### 查看回测性能统计
```sql
SELECT 
    COUNT(*) as total_backtests,
    AVG(CAST(json_extract(results, '$.total_return') AS FLOAT)) as avg_return,
    MAX(CAST(json_extract(results, '$.total_return') AS FLOAT)) as max_return,
    MIN(CAST(json_extract(results, '$.total_return') AS FLOAT)) as min_return
FROM backtests
WHERE results IS NOT NULL;
```

### 5. 数据维护操作

#### 清理重复数据
```sql
-- 删除重复的股票数据（保留最新的一条）
DELETE FROM stock_data 
WHERE id NOT IN (
    SELECT MAX(id) 
    FROM stock_data 
    GROUP BY stock_id, date
);
```

#### 更新股票最后更新时间
```sql
UPDATE stocks 
SET last_updated = (
    SELECT MAX(date) 
    FROM stock_data 
    WHERE stock_id = stocks.id
);
```

#### 备份数据库
```bash
# 在终端中
cp backtesting.db backtesting_backup_$(date +%Y%m%d_%H%M%S).db
```

#### 恢复数据库
```bash
# 在终端中
cp backtesting_backup_20250120_143000.db backtesting.db
```

### 6. 性能优化

#### 查看现有索引
```sql
-- 查看所有索引
SELECT name, sql FROM sqlite_master WHERE type = 'index';
```

#### 创建索引（如果需要）
```sql
-- 为常用查询创建索引
CREATE INDEX idx_stock_data_stock_date ON stock_data(stock_id, date);
CREATE INDEX idx_trades_backtest_date ON trades(backtest_id, datetime);
CREATE INDEX idx_stocks_symbol ON stocks(symbol);
```

### 7. 导出数据

#### 导出为CSV
```sql
-- 在SQLite命令行中
.mode csv
.headers on
.output stock_data.csv
SELECT * FROM stock_data WHERE stock_id = 1;
.output stdout
```

#### 导出表结构
```sql
-- 导出所有表的创建语句
.output schema.sql
.schema
.output stdout
```

### 8. 实用技巧

#### 查看数据库大小
```sql
SELECT 
    name,
    page_count * page_size as size_bytes,
    (page_count * page_size) / 1024.0 / 1024.0 as size_mb
FROM pragma_page_count(), pragma_page_size();
```

#### 查看表的行数
```sql
SELECT 
    'stocks' as table_name, COUNT(*) as row_count FROM stocks
UNION ALL
SELECT 'stock_data', COUNT(*) FROM stock_data
UNION ALL
SELECT 'strategies', COUNT(*) FROM strategies
UNION ALL
SELECT 'backtests', COUNT(*) FROM backtests
UNION ALL
SELECT 'trades', COUNT(*) FROM trades;
```

#### 查看最近的数据更新
```sql
SELECT 
    s.symbol,
    s.name,
    s.last_updated,
    MAX(sd.date) as latest_data_date
FROM stocks s
LEFT JOIN stock_data sd ON s.id = sd.stock_id
GROUP BY s.id, s.symbol, s.name, s.last_updated
ORDER BY s.last_updated DESC;
```

## 注意事项

1. **备份重要**：在进行重要操作前，请先备份数据库文件
2. **权限控制**：确保数据库文件有适当的读写权限
3. **并发访问**：SQLite 不支持高并发写入，建议在应用层面控制并发
4. **数据完整性**：定期检查数据完整性，确保外键约束正确
5. **性能监控**：对于大数据量，注意查询性能，合理使用索引

## 故障排除

### 常见问题

1. **数据库锁定**
   ```bash
   # 检查是否有其他进程在使用数据库
   lsof backtesting.db
   ```

2. **权限问题**
   ```bash
   # 修复权限
   chmod 644 backtesting.db
   ```

3. **数据库损坏**
   ```bash
   # 检查数据库完整性
   sqlite3 backtesting.db "PRAGMA integrity_check;"
   ```

4. **空间不足**
   ```bash
   # 查看数据库大小
   ls -lh backtesting.db
   ```

这个文档提供了完整的数据库使用指南，包括表结构、字段含义和常用操作。建议将此文档保存在项目的 `docs` 目录中，方便团队成员查阅。
