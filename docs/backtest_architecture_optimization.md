# 回测数据架构优化说明

## 概述

本次优化将原有的单一 `backtests` 表架构改进为 **状态表 + 流水表** 的双表架构，以提升用户体验和系统性能。

## 架构对比

### 原架构问题
- **数据冗余**：每次回测更新都会创建新记录，导致大量重复数据
- **用户体验差**：用户看到的是所有历史流水，而不是最新的回测状态
- **查询效率低**：需要从大量历史记录中筛选最新数据
- **存储浪费**：相同策略的多次回测保存了大量重复信息

### 新架构优势
- **清晰的数据结构**：状态表存储最新状态，历史表记录每次更新
- **更好的用户体验**：主列表只显示最新状态，历史记录按需查看
- **更高的查询性能**：状态表数据量小，查询速度快
- **完整的数据审计**：保留完整的历史记录用于版本对比和审计

## 新架构设计

### 1. 状态表 (`backtest_status`)
存储每个回测任务的最新状态和结果：

```sql
CREATE TABLE backtest_status (
    id INTEGER PRIMARY KEY,
    name VARCHAR UNIQUE,  -- 回测名称，唯一
    description TEXT,
    strategy_id INTEGER,
    strategy_snapshot_id INTEGER NOT NULL,
    start_date DATETIME,
    end_date DATETIME,
    initial_capital FLOAT,
    instruments JSON,
    parameters JSON,
    position_config JSON,
    results JSON,
    equity_curve JSON,
    trade_records JSON,
    performance_metrics JSON,
    status VARCHAR DEFAULT 'running',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);
```

### 2. 流水表 (`backtest_history`)
记录每次回测更新的历史：

```sql
CREATE TABLE backtest_history (
    id INTEGER PRIMARY KEY,
    status_id INTEGER NOT NULL,
    start_date DATETIME,
    end_date DATETIME,
    initial_capital FLOAT,
    instruments JSON,
    parameters JSON,
    position_config JSON,
    results JSON,
    equity_curve JSON,
    trade_records JSON,
    performance_metrics JSON,
    status VARCHAR DEFAULT 'running',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    operation_type VARCHAR DEFAULT 'create'  -- create, update, rerun
);
```

## 前端展示优化

### 1. 回测列表页面
- **数据来源**：`backtest_status` 表
- **显示内容**：每个回测任务的最新状态
- **操作按钮**：
  - "查看详情" - 显示最新结果
  - "查看历史" - 跳转到历史记录页面
  - "更新回测" - 重新运行回测
  - "删除" - 删除回测及其历史记录

### 2. 回测历史详情页面
- **数据来源**：`backtest_history` 表
- **显示内容**：该回测的所有历史记录
- **功能特性**：
  - 按时间倒序显示历史记录
  - 显示每次更新的操作类型（创建/更新）
  - 支持查看每次更新的详细结果
  - 支持结果对比分析

## API 接口

### 新增接口

#### 1. 回测状态管理
- `GET /api/backtest-status/list` - 获取回测状态列表
- `GET /api/backtest-status/{id}` - 获取回测状态详情
- `GET /api/backtest-status/{id}/history` - 获取回测历史记录
- `POST /api/backtest-status/{id}/update` - 更新回测状态
- `DELETE /api/backtest-status/{id}` - 删除回测状态
- `GET /api/backtest-status/stats/summary` - 获取统计摘要

#### 2. 兼容性接口
- 原有的 `/api/backtest/*` 接口继续工作，保持向后兼容

## 数据迁移

### 迁移脚本
使用 `scripts/migrate_backtest_architecture.py` 进行数据迁移：

```bash
# 分析现有数据
python scripts/migrate_backtest_architecture.py --analyze-only

# 模拟迁移（不实际修改数据）
python scripts/migrate_backtest_architecture.py --dry-run

# 执行实际迁移
python scripts/migrate_backtest_architecture.py

# 验证迁移结果
python scripts/migrate_backtest_architecture.py --verify-only
```

### 迁移策略
1. **按回测名称分组**：每个名称创建一个状态记录
2. **最新记录作为状态**：使用最新创建的回测记录作为状态记录
3. **所有记录作为历史**：将所有历史记录迁移到历史表
4. **保持向后兼容**：同时保留原有表结构

## 测试验证

### 测试脚本
使用 `scripts/test_backtest_architecture.py` 进行功能测试：

```bash
# 运行所有测试
python scripts/test_backtest_architecture.py

# 仅清理测试数据
python scripts/test_backtest_architecture.py --cleanup-only
```

### 测试内容
1. **创建状态记录**：测试状态记录的创建功能
2. **创建历史记录**：测试历史记录的创建功能
3. **更新状态记录**：测试状态记录的更新功能
4. **查询操作**：测试各种查询操作
5. **数据完整性**：验证数据完整性和约束
6. **性能测试**：测试查询性能

## 部署步骤

### 1. 数据库迁移
```bash
# 1. 备份现有数据
python scripts/migrate_backtest_architecture.py --create-backup

# 2. 分析现有数据
python scripts/migrate_backtest_architecture.py --analyze-only

# 3. 执行迁移
python scripts/migrate_backtest_architecture.py

# 4. 验证迁移结果
python scripts/migrate_backtest_architecture.py --verify-only
```

### 2. 后端部署
```bash
# 1. 更新代码
git pull origin main

# 2. 重启后端服务
systemctl restart backtest-api

# 3. 验证API接口
curl http://localhost:8000/api/backtest-status/stats/summary
```

### 3. 前端部署
```bash
# 1. 构建前端
cd src/frontend
npm run build

# 2. 部署到服务器
# 将 dist 目录内容部署到 Web 服务器
```

### 4. 功能验证
```bash
# 1. 运行测试脚本
python scripts/test_backtest_architecture.py

# 2. 手动测试前端功能
# - 访问回测历史页面
# - 测试查看详情功能
# - 测试查看历史功能
# - 测试更新回测功能
```

## 回滚方案

如果新架构出现问题，可以快速回滚：

### 1. 数据库回滚
```bash
# 恢复备份表
DROP TABLE IF EXISTS backtests;
ALTER TABLE backtests_backup RENAME TO backtests;
```

### 2. 代码回滚
```bash
# 回滚到之前的版本
git checkout <previous-commit>
```

### 3. 前端回滚
```bash
# 回滚前端代码
git checkout <previous-commit>
npm run build
```

## 性能优化建议

### 1. 数据库索引
```sql
-- 状态表索引
CREATE INDEX idx_backtest_status_name ON backtest_status(name);
CREATE INDEX idx_backtest_status_updated_at ON backtest_status(updated_at);
CREATE INDEX idx_backtest_status_status ON backtest_status(status);

-- 历史表索引
CREATE INDEX idx_backtest_history_status_id ON backtest_history(status_id);
CREATE INDEX idx_backtest_history_created_at ON backtest_history(created_at);
CREATE INDEX idx_backtest_history_operation_type ON backtest_history(operation_type);
```

### 2. 查询优化
- 使用分页查询避免一次性加载大量数据
- 使用适当的 JOIN 查询减少数据库往返
- 缓存频繁查询的结果

### 3. 数据归档
- 定期归档旧的历史记录
- 压缩长期不访问的数据
- 考虑使用分区表处理大量历史数据

## 监控和维护

### 1. 性能监控
- 监控查询响应时间
- 监控数据库连接数
- 监控存储空间使用

### 2. 数据维护
- 定期清理测试数据
- 定期备份重要数据
- 监控数据完整性

### 3. 用户反馈
- 收集用户对新界面的反馈
- 监控用户使用模式
- 根据反馈持续优化

## 总结

新的回测数据架构通过状态表和历史表的分离，实现了：

1. **更好的用户体验**：主列表只显示最新状态，界面更清晰
2. **更高的查询性能**：状态表数据量小，查询速度快
3. **完整的数据审计**：保留完整的历史记录
4. **向后兼容性**：保持原有API接口的兼容性

这个架构为回测系统提供了更好的可扩展性和维护性，同时保持了良好的用户体验。
