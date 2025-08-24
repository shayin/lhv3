# 数据库优化说明

## 概述

为了提高系统性能，我们对数据库结构进行了优化，将股票数据的统计信息（总记录数、开始日期、结束日期）存储在`stocks`表中，避免了每次查询时都需要对`stock_data`表进行复杂的统计计算。

## 优化内容

### 1. 数据库表结构优化

#### 新增字段
在`stocks`表中添加了以下字段：
- `total_records`: 总记录数
- `first_date`: 数据开始日期
- `last_date`: 数据结束日期

#### 数据库变更
```sql
-- 添加新字段
ALTER TABLE stocks ADD COLUMN total_records INTEGER DEFAULT 0;
ALTER TABLE stocks ADD COLUMN first_date DATE;
ALTER TABLE stocks ADD COLUMN last_date DATE;

-- 更新现有数据
UPDATE stocks SET 
    total_records = (SELECT COUNT(*) FROM stock_data WHERE stock_data.stock_id = stocks.id),
    first_date = (SELECT MIN(date) FROM stock_data WHERE stock_data.stock_id = stocks.id),
    last_date = (SELECT MAX(date) FROM stock_data WHERE stock_data.stock_id = stocks.id);
```

### 2. 后端API优化

#### 性能提升
- **股票列表API** (`/api/data/stocks`): 从复杂的JOIN查询简化为直接读取`stocks`表
- **时间范围API** (`/api/data/stock/{stock_id}/date-range`): 直接返回`stocks`表中的统计信息

#### 事务性更新
在数据导入和更新时，同时更新`stock_data`表和`stocks`表的统计信息，确保数据一致性。

### 3. 前端优化

#### 性能提升
- 减少了API调用次数（从N+1次减少到1次）
- 提高了页面加载速度
- 保持了所有原有功能

## 性能对比

### 优化前
- 股票列表API: 需要为每个股票查询`stock_data`表进行统计
- 前端加载: 需要N+1次API调用（1次获取股票列表 + N次获取时间范围）
- 响应时间: 较慢，特别是在数据量大的情况下

### 优化后
- 股票列表API: 直接读取`stocks`表的统计字段
- 前端加载: 只需要1次API调用
- 响应时间: 显著提升，响应时间从几百毫秒降低到几十毫秒

## 维护工具

### 数据库维护脚本
提供了`scripts/update_stock_statistics.py`脚本用于维护统计信息：

```bash
# 显示当前统计信息
python3 scripts/update_stock_statistics.py --show

# 更新所有股票的统计信息
python3 scripts/update_stock_statistics.py --update

# 显示并更新
python3 scripts/update_stock_statistics.py --show --update
```

### 自动更新机制
- 在数据导入时自动更新统计信息
- 在数据更新时自动更新统计信息
- 确保统计信息与实际情况保持一致

## 使用说明

### 1. 查看股票列表
```bash
curl -X GET "http://localhost:8000/api/data/stocks"
```

返回数据包含：
- `data_count`: 总记录数
- `first_date`: 数据开始日期
- `last_date`: 数据结束日期

### 2. 更新股票数据
```bash
curl -X POST "http://localhost:8000/api/data/update/{stock_id}"
```

更新后会自动更新`stocks`表中的统计信息。

### 3. 手动更新统计信息
如果发现统计信息不准确，可以手动更新：

```bash
python3 scripts/update_stock_statistics.py --update
```

## 注意事项

### 1. 数据一致性
- 统计信息会在数据导入和更新时自动更新
- 如果手动修改了`stock_data`表，需要运行维护脚本更新统计信息

### 2. 性能监控
- 定期检查API响应时间
- 监控数据库查询性能
- 关注统计信息的准确性

### 3. 备份策略
在进行数据库结构变更前，建议备份数据库：

```bash
cp backtesting.db backtesting_backup_$(date +%Y%m%d_%H%M%S).db
```

## 故障排除

### 1. 统计信息不准确
```bash
# 重新计算所有股票的统计信息
python3 scripts/update_stock_statistics.py --update
```

### 2. API响应慢
- 检查数据库索引是否正确
- 确认统计信息是否已更新
- 查看服务器日志

### 3. 数据不一致
- 检查事务是否正确提交
- 确认更新函数是否被正确调用
- 验证数据库约束是否生效

## 总结

通过这次优化，我们实现了：

1. **性能提升**: API响应时间显著降低
2. **用户体验改善**: 前端页面加载速度更快
3. **数据一致性**: 通过事务性更新确保统计信息准确
4. **可维护性**: 提供了完善的维护工具和文档

这个优化方案既保持了功能的完整性，又大大提升了系统性能，是一个成功的数据库优化案例。
