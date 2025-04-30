# 量化交易系统

一个集策略开发、回测分析、数据可视化于一体的量化交易平台。

## 项目概述

本项目是一个具有完整界面的量化交易系统，支持策略配置和策略回测。系统包括以下核心功能：

- **数据管理**：支持从多种数据源获取市场数据，包括股票、期货等
- **策略配置**：提供可视化策略编辑器和代码编辑器，支持多种常用策略模板
- **回测分析**：高性能回测引擎，支持详细的绩效分析和可视化报告
- **参数优化**：支持策略参数优化，找到最优参数组合

## 技术栈

### 前端
- React + TypeScript
- Ant Design 组件库
- ECharts 图表库
- Vite 构建工具

### 后端
- Python + FastAPI
- pandas, numpy 数据处理
- TA-Lib 技术分析
- SQLAlchemy ORM
- 多数据源支持 (Yahoo Finance, AKShare等)

## 安装指南

### 前提条件
- Node.js >= 16.0.0
- Python >= 3.8
- pip 或 conda 包管理器

### 后端安装
1. 创建并激活Python虚拟环境（推荐）：
```bash
python3 -m venv venv
source venv/bin/activate  # 在Windows上使用 venv\Scripts\activate
```

2. 安装依赖：
```bash
pip3 install -r requirements.txt
```

3. 安装TA-Lib（可能需要额外步骤）：
   - 对于Windows用户，您可能需要从以下地址下载预编译的wheel文件：
     https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
   - 对于MacOS用户，可以使用Homebrew：
     ```
     brew install ta-lib
     pip3 install ta-lib
     ```
   - 对于Linux用户，您可能需要先编译TA-Lib库：
     ```
     wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
     tar -xzf ta-lib-0.4.0-src.tar.gz
     cd ta-lib/
     ./configure --prefix=/usr
     make
     sudo make install
     pip3 install ta-lib
     ```

### 前端安装
1. 进入前端目录：
```bash
cd src/frontend
```

2. 安装依赖：
```bash
npm install
```

## 启动应用

### 启动后端
```bash
cd src/backend
python3 main.py
```
后端API将在 http://localhost:8000 启动，可通过 http://localhost:8000/docs 访问API文档。

### 启动前端
```bash
cd src/frontend
npm run dev
```
前端应用将在 http://localhost:3000 启动。

## 项目结构
```
.
├── data/                      # 数据目录
│   ├── raw/                   # 原始数据
│   └── processed/             # 处理后的数据
├── requirements.txt           # Python依赖
├── src/
│   ├── backend/               # 后端代码
│   │   ├── api/               # API服务
│   │   ├── backtest/          # 回测模块
│   │   ├── data/              # 数据获取和处理
│   │   ├── models/            # 数据库模型
│   │   ├── strategy/          # 策略模板
│   │   ├── config.py          # 配置文件
│   │   └── main.py            # 主入口
│   └── frontend/              # 前端代码
│       ├── public/            # 静态资源
│       ├── src/               # 源代码
│       ├── package.json       # npm配置
│       └── vite.config.ts     # Vite配置
└── tests/                     # 测试代码
```

## 一期开发功能

一期开发主要完成以下核心功能：

1. **数据管理模块**：
   - 支持多种数据源接入
   - 数据清洗与预处理
   - 数据可视化

2. **策略配置模块**：
   - 策略编辑器
   - 内置常用技术指标
   - 策略模板库

3. **回测模块**：
   - 高性能回测引擎
   - 真实交易模拟
   - 绩效评估与可视化

## 许可证

MIT

## 联系方式

如有问题或建议，请提交Issue或者发送邮件至 [your-email@example.com](mailto:your-email@example.com) 