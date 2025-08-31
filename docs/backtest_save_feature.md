# 回测保存和查看功能

## 功能概述

本功能实现了完整的回测保存和查看机制，允许用户保存回测结果并随时查看历史回测记录。由于策略会随时变化，系统会保存回测时的策略镜像，确保历史回测的完整性和可追溯性。

## 核心特性

### 1. 策略镜像保存
- **策略快照表** (`strategy_snapshots`): 保存回测时的策略完整镜像
- **策略代码保存**: 保存策略的完整代码，确保可重现
- **策略参数保存**: 保存策略的参数配置
- **策略模板信息**: 保存策略的模板类型和描述

### 2. 回测记录管理
- **回测表** (`backtests`): 存储回测的基本信息和结果
- **完整数据保存**: 包括权益曲线、交易记录、性能指标等
- **仓位配置保存**: 保存回测时的仓位控制配置
- **状态管理**: 支持运行中、已完成、失败等状态

### 3. 前端功能
- **保存按钮**: 在回测分析页面添加保存功能
- **保存对话框**: 用户可输入回测名称和描述
- **回测历史页面**: 专门的回测历史管理页面
- **详情查看**: 可查看回测的完整信息和结果
- **删除功能**: 支持删除不需要的回测记录

## 数据库设计

### 策略快照表 (strategy_snapshots)
```sql
CREATE TABLE strategy_snapshots (
    id INTEGER PRIMARY KEY,
    strategy_id INTEGER,           -- 关联的策略ID
    name VARCHAR,                  -- 策略名称
    description VARCHAR,           -- 策略描述
    code TEXT,                     -- 策略代码镜像
    parameters TEXT,               -- 策略参数镜像
    template VARCHAR,              -- 策略模板类型
    created_at DATETIME,           -- 创建时间
    FOREIGN KEY(strategy_id) REFERENCES strategies (id)
);
```

### 回测表 (backtests)
```sql
CREATE TABLE backtests (
    id INTEGER PRIMARY KEY,
    name VARCHAR,                  -- 回测名称
    description VARCHAR,           -- 回测描述
    strategy_id INTEGER,           -- 当前策略ID（可能为空）
    strategy_snapshot_id INTEGER,  -- 策略快照ID（必填）
    start_date DATETIME,           -- 回测开始日期
    end_date DATETIME,             -- 回测结束日期
    initial_capital FLOAT,         -- 初始资金
    instruments JSON,              -- 回测标的
    parameters JSON,               -- 回测参数
    position_config JSON,          -- 仓位控制配置
    results JSON,                  -- 回测结果
    equity_curve JSON,             -- 权益曲线数据
    trade_records JSON,            -- 交易记录
    performance_metrics JSON,      -- 性能指标
    status VARCHAR,                -- 状态
    created_at DATETIME,           -- 创建时间
    completed_at DATETIME,         -- 完成时间
    FOREIGN KEY(strategy_id) REFERENCES strategies (id),
    FOREIGN KEY(strategy_snapshot_id) REFERENCES strategy_snapshots (id)
);
```

## API接口

### 1. 保存回测
```http
POST /api/backtest/save
Content-Type: application/json

{
    "name": "回测名称",
    "description": "回测描述",
    "strategy_id": 1,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 100000,
    "instruments": ["AAPL"],
    "parameters": {...},
    "position_config": {...}
}
```

### 2. 获取回测列表
```http
GET /api/backtest/list?page=1&size=20
```

### 3. 获取回测详情
```http
GET /api/backtest/{backtest_id}
```

### 4. 删除回测
```http
DELETE /api/backtest/{backtest_id}
```

## 前端页面

### 1. 回测分析页面 (`/backtest`)
- 添加保存按钮
- 保存对话框
- 保存成功后跳转提示

### 2. 回测历史页面 (`/backtest/history`)
- 回测列表展示
- 性能指标显示
- 详情查看功能
- 删除功能

### 3. 导航菜单
- 回测管理子菜单
  - 回测分析
  - 回测历史

## 使用流程

### 1. 运行回测
1. 在回测分析页面配置参数
2. 点击"运行回测"按钮
3. 查看回测结果

### 2. 保存回测
1. 点击"保存回测"按钮
2. 输入回测名称和描述
3. 确认保存
4. 选择是否跳转到回测历史页面

### 3. 查看历史
1. 在导航菜单选择"回测历史"
2. 查看所有保存的回测记录
3. 点击"查看"按钮查看详情
4. 点击"删除"按钮删除不需要的记录

## 技术实现

### 后端实现
- **数据模型**: 扩展了策略和回测模型
- **API路由**: 新增回测保存相关API
- **服务层**: 在BacktestService中添加保存功能
- **数据库迁移**: 创建了迁移脚本

### 前端实现
- **状态管理**: 添加保存相关状态
- **API调用**: 集成保存和查看API
- **UI组件**: 新增保存对话框和历史页面
- **路由配置**: 添加回测历史路由

## 测试验证

### 功能测试
- ✅ 保存回测功能正常
- ✅ 获取回测列表正常
- ✅ 获取回测详情正常
- ✅ 删除回测功能正常
- ✅ 策略镜像保存正常

### 数据完整性
- ✅ 策略快照正确保存
- ✅ 回测记录完整保存
- ✅ 关联关系正确建立
- ✅ 数据一致性验证通过

## 优势特点

1. **完整性**: 保存策略的完整镜像，确保历史回测的可重现性
2. **可追溯性**: 每个回测都关联到具体的策略版本
3. **易用性**: 简单的保存和查看流程
4. **扩展性**: 支持多种策略类型和参数配置
5. **性能**: 合理的数据库设计和索引优化

## 未来扩展

1. **回测对比**: 支持多个回测结果的对比分析
2. **回测报告**: 生成详细的回测报告
3. **回测分享**: 支持回测结果的分享和导出
4. **回测模板**: 支持保存常用的回测配置为模板
5. **批量操作**: 支持批量删除和管理回测记录
