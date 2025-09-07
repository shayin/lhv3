#!/bin/bash

# 回测新架构设置脚本
# 用于快速设置和测试新的回测数据架构

set -e  # 遇到错误立即退出

echo "🚀 开始设置回测新架构..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python环境
check_python() {
    print_info "检查Python环境..."
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi
    print_success "Python3 环境正常"
}

# 检查项目依赖
check_dependencies() {
    print_info "检查项目依赖..."
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt 文件不存在"
        exit 1
    fi
    
    # 检查关键依赖
    python3 -c "import sqlalchemy" 2>/dev/null || {
        print_error "SQLAlchemy 未安装，请运行: pip install -r requirements.txt"
        exit 1
    }
    
    print_success "项目依赖检查通过"
}

# 创建数据库表
create_tables() {
    print_info "创建新的数据库表..."
    python3 -c "
from src.backend.models import init_db
engine = init_db()
print('数据库表创建完成')
" || {
        print_error "创建数据库表失败"
        exit 1
    }
    print_success "数据库表创建成功"
}

# 分析现有数据
analyze_data() {
    print_info "分析现有回测数据..."
    python3 scripts/migrate_backtest_architecture.py --analyze-only || {
        print_warning "数据分析失败，可能是数据库中没有数据"
    }
}

# 执行数据迁移
migrate_data() {
    print_info "执行数据迁移..."
    read -p "是否要执行数据迁移？这将修改数据库结构 (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 创建备份
        print_info "创建数据备份..."
        python3 scripts/migrate_backtest_architecture.py --create-backup
        
        # 执行迁移
        print_info "执行数据迁移..."
        python3 scripts/migrate_backtest_architecture.py
        
        # 验证迁移结果
        print_info "验证迁移结果..."
        python3 scripts/migrate_backtest_architecture.py --verify-only
        
        print_success "数据迁移完成"
    else
        print_warning "跳过数据迁移"
    fi
}

# 运行测试
run_tests() {
    print_info "运行架构测试..."
    python3 scripts/test_backtest_architecture.py || {
        print_error "测试失败"
        exit 1
    }
    print_success "所有测试通过"
}

# 启动后端服务
start_backend() {
    print_info "启动后端服务..."
    if [ -f "src/backend/main.py" ]; then
        print_info "后端服务启动命令: python3 src/backend/main.py"
        print_info "请在新终端中运行上述命令"
    else
        print_warning "未找到后端启动文件"
    fi
}

# 构建前端
build_frontend() {
    print_info "构建前端..."
    if [ -d "src/frontend" ]; then
        cd src/frontend
        if [ -f "package.json" ]; then
            npm install
            npm run build
            print_success "前端构建完成"
        else
            print_warning "未找到前端package.json文件"
        fi
        cd ../..
    else
        print_warning "未找到前端目录"
    fi
}

# 显示使用说明
show_usage() {
    echo
    echo "🎉 回测新架构设置完成！"
    echo
    echo "📋 接下来的步骤："
    echo "1. 启动后端服务: python3 src/backend/main.py"
    echo "2. 启动前端服务: cd src/frontend && npm run dev"
    echo "3. 访问回测历史页面测试新功能"
    echo
    echo "🔧 可用的管理命令："
    echo "- 数据迁移: python3 scripts/migrate_backtest_architecture.py"
    echo "- 运行测试: python3 scripts/test_backtest_architecture.py"
    echo "- 清理测试数据: python3 scripts/test_backtest_architecture.py --cleanup-only"
    echo
    echo "📚 详细文档: docs/backtest_architecture_optimization.md"
    echo
}

# 主函数
main() {
    echo "=========================================="
    echo "    回测数据架构优化设置脚本"
    echo "=========================================="
    echo
    
    # 检查环境
    check_python
    check_dependencies
    
    # 创建表结构
    create_tables
    
    # 分析现有数据
    analyze_data
    
    # 执行数据迁移
    migrate_data
    
    # 运行测试
    run_tests
    
    # 构建前端
    build_frontend
    
    # 显示使用说明
    show_usage
}

# 错误处理
trap 'print_error "脚本执行失败，请检查错误信息"; exit 1' ERR

# 执行主函数
main "$@"
