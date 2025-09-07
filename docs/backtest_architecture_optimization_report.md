# 回测数据存储架构优化报告

## 项目概述

本次优化将原有的单一回测表（`backtests`）重构为状态表（`backtest_status`）+ 历史表（`backtest_history`）的双表架构，提升了用户体验和系统性能。

## 优化目标

- **用户体验提升**：前端默认显示最新回测数据，避免显示所有历史流水
- **数据管理优化**：清晰分离当前状态和历史记录
- **系统性能提升**：减少不必要的数据查询和传输
- **功能完整性**：保持所有原有功能，增加历史记录查看能力

## 架构设计

### 数据库表结构

#### 1. BacktestStatus（回测状态表）
存储每个回测策略的最新状态信息：
- 基本信息：名称、描述、策略ID
- 回测参数：时间范围、初始资金、标的、参数配置
- 回测结果：收益曲线、交易记录、绩效指标
- 状态信息：状态、创建时间、更新时间、完成时间

#### 2. BacktestHistory（回测历史表）
记录每次回测更新的历史信息：
- 关联状态：通过status_id关联到BacktestStatus
- 完整记录：包含所有回测参数和结果
- 操作类型：区分创建、更新等操作类型
- 时间戳：记录每次操作的时间

### 关系设计
- 一对多关系：一个BacktestStatus对应多个BacktestHistory记录
- 级联删除：删除状态记录时自动删除相关历史记录

## 实现细节

### 后端实现

#### 1. 数据模型（src/backend/models/strategy.py）
```python
class BacktestStatus(Base):
    """回测状态表 - 存储最新状态"""
    __tablename__ = "backtest_status"
    # 完整的字段定义...

class BacktestHistory(Base):
    """回测历史表 - 记录每次更新"""
    __tablename__ = "backtest_history"
    # 完整的字段定义...
```

#### 2. API路由（src/backend/api/backtest_status_routes.py）
- `GET /api/backtest-status/list` - 获取回测状态列表
- `GET /api/backtest-status/{id}` - 获取特定回测状态详情
- `POST /api/backtest-status/{id}/update` - 更新回测状态
- `DELETE /api/backtest-status/{id}` - 删除回测状态
- `GET /api/backtest-status/{id}/history` - 获取回测历史记录

#### 3. 更新机制
- 支持部分参数更新：只更新提供的参数，未提供的保持原值
- 自动重新运行回测：使用更新后的参数重新执行回测
- 历史记录创建：每次更新都创建新的历史记录

### 前端实现

#### 1. 回测历史页面（src/frontend/src/pages/BacktestHistory.tsx）
- 显示最新回测状态列表
- 支持更新、删除操作
- 提供历史记录查看入口

#### 2. 历史详情页面（src/frontend/src/pages/BacktestHistoryDetail.tsx）
- 显示特定回测的所有历史记录
- 按时间倒序排列
- 展示每次更新的参数变化

## 数据迁移

### 迁移脚本（scripts/migrate_backtest_architecture.py）
- 分析现有数据：统计回测记录数量
- 数据迁移：将backtests表数据迁移到新架构
- 数据验证：确保迁移数据的完整性
- 支持干运行模式：预览迁移结果

### 向后兼容
- 保留原有backtests表
- 新保存的回测数据同时写入新旧表
- 确保现有功能不受影响

## 测试验证

### 测试脚本
1. **test_backtest_architecture.py** - 基础架构测试
2. **test_save_backtest.py** - 保存功能测试
3. **test_update_backtest.py** - 更新功能测试
4. **test_update_with_params.py** - 参数更新测试

### 测试覆盖
- 数据模型创建和关系
- API端点功能
- 参数更新逻辑
- 历史记录创建
- 数据一致性验证

## 关键修复

### 1. 数据库表创建问题
**问题**：新表无法创建
**解决**：确保Base.metadata.create_all()正确调用

### 2. 保存功能问题
**问题**：前端保存仍写入旧表
**解决**：修改backtest_service.py的_save_backtest_result方法

### 3. 更新功能问题
**问题**：更新操作无效果
**解决**：实现完整的更新逻辑，支持参数更新

### 4. 参数更新问题
**问题**：更新时使用旧参数而非新参数
**解决**：创建UpdateBacktestRequest模型，支持部分参数更新

## 性能优化

### 查询优化
- 状态表查询：只获取最新数据，减少数据传输
- 历史表查询：按需加载，支持分页
- 索引优化：在关键字段上建立索引

### 存储优化
- 数据去重：避免重复存储相同的历史记录
- 压缩存储：对大型JSON字段进行压缩
- 清理机制：定期清理过期的历史记录

## 用户体验改进

### 界面优化
- 默认显示最新状态：用户主要关注当前数据
- 历史记录入口：需要时可查看完整历史
- 操作反馈：清晰的更新和删除确认

### 功能增强
- 参数对比：显示更新前后的参数变化
- 时间线视图：按时间顺序展示历史记录
- 批量操作：支持批量删除历史记录

## 部署说明

### 1. 数据库迁移
```bash
# 运行迁移脚本
python3 scripts/migrate_backtest_architecture.py

# 验证迁移结果
python3 scripts/test_backtest_architecture.py
```

### 2. 服务重启
```bash
# 重启后端服务
pkill -f "python3 src/backend/main.py"
python3 src/backend/main.py
```

### 3. 前端更新
前端代码已更新，无需额外配置。

## 监控和维护

### 数据监控
- 定期检查数据一致性
- 监控存储空间使用
- 跟踪查询性能

### 维护任务
- 定期清理过期历史记录
- 优化数据库索引
- 更新API文档

## 总结

本次架构优化成功实现了以下目标：

1. **用户体验显著提升**：前端默认显示最新数据，减少信息噪音
2. **数据管理更加清晰**：状态和历史分离，便于维护和查询
3. **功能完整性保持**：所有原有功能正常工作，新增历史查看功能
4. **系统性能优化**：减少不必要的数据查询和传输
5. **向后兼容性**：平滑过渡，不影响现有功能

架构优化为后续功能扩展奠定了良好基础，支持更复杂的回测管理和分析需求。

## 技术栈

- **后端**：Python, FastAPI, SQLAlchemy, Pydantic
- **前端**：React, TypeScript, Ant Design
- **数据库**：SQLite
- **测试**：Python unittest

## 文件清单

### 新增文件
- `src/backend/models/strategy.py` - 新数据模型
- `src/backend/api/backtest_status_routes.py` - 新API路由
- `src/frontend/src/pages/BacktestHistoryDetail.tsx` - 历史详情页面
- `scripts/migrate_backtest_architecture.py` - 数据迁移脚本
- `scripts/test_*.py` - 各种测试脚本

### 修改文件
- `src/backend/models/__init__.py` - 导入新模型
- `src/backend/api/app.py` - 注册新路由
- `src/backend/api/backtest_routes.py` - 更新保存逻辑
- `src/backend/api/backtest_service.py` - 更新服务逻辑
- `src/frontend/src/pages/BacktestHistory.tsx` - 更新前端页面

---

**优化完成时间**：2024年12月
**负责人**：AI助手
**状态**：已完成并测试通过
