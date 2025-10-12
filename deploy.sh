#!/bin/bash

# 量化交易系统部署和服务管理脚本
# 支持前端构建、后端服务启动/重启等功能

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/src/frontend"
BACKEND_DIR="$PROJECT_ROOT/src/backend"
PID_FILE="$PROJECT_ROOT/backend.pid"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 命令未找到，请先安装"
        exit 1
    fi
}

# 检查目录是否存在
check_directory() {
    if [ ! -d "$1" ]; then
        log_error "目录不存在: $1"
        exit 1
    fi
}

# 构建前端
build_frontend() {
    log_info "开始构建前端..."
    
    check_directory "$FRONTEND_DIR"
    check_command "npm"
    
    cd "$FRONTEND_DIR"
    
    # 检查是否存在node_modules
    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm install
        if [ $? -ne 0 ]; then
            log_error "前端依赖安装失败"
            exit 1
        fi
    fi
    
    # 构建前端
    log_info "执行前端构建..."
    npm run build
    
    if [ $? -eq 0 ]; then
        log_success "前端构建完成"
        return 0
    else
        log_error "前端构建失败"
        exit 1
    fi
}

# 检查后端进程是否运行
is_backend_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p $pid > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# 停止后端服务
stop_backend() {
    log_info "停止后端服务..."
    
    if is_backend_running; then
        local pid=$(cat "$PID_FILE")
        log_info "发现运行中的后端进程 (PID: $pid)，正在停止..."
        
        # 优雅停止
        kill -TERM $pid
        sleep 3
        
        # 检查是否已停止
        if ps -p $pid > /dev/null 2>&1; then
            log_warning "进程未响应TERM信号，使用KILL信号强制停止..."
            kill -KILL $pid
            sleep 1
        fi
        
        rm -f "$PID_FILE"
        log_success "后端服务已停止"
    else
        log_info "后端服务未运行"
    fi
}

# 启动后端服务
start_backend() {
    log_info "启动后端服务..."
    
    check_directory "$BACKEND_DIR"
    
    # 检查Python环境
    if command -v python3.9 &> /dev/null; then
        PYTHON_CMD="python3.9"
    elif command -v python3.8 &> /dev/null; then
        PYTHON_CMD="python3.8"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        log_error "未找到Python3环境"
        exit 1
    fi
    
    cd "$BACKEND_DIR"
    
    # 检查main.py是否存在
    if [ ! -f "main.py" ]; then
        log_error "未找到main.py文件"
        exit 1
    fi
    
    # 后台启动服务
    log_info "使用 $PYTHON_CMD 启动后端服务..."
    nohup $PYTHON_CMD main.py > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
    local pid=$!
    
    # 保存PID
    echo $pid > "$PID_FILE"
    
    # 等待服务启动
    sleep 3
    
    # 检查服务是否成功启动
    if ps -p $pid > /dev/null 2>&1; then
        log_success "后端服务启动成功 (PID: $pid)"
        log_info "日志文件: $PROJECT_ROOT/logs/backend.log"
    else
        log_error "后端服务启动失败"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# 重启后端服务
restart_backend() {
    log_info "重启后端服务..."
    stop_backend
    sleep 2
    start_backend
}

# 查看后端状态
status_backend() {
    if is_backend_running; then
        local pid=$(cat "$PID_FILE")
        log_success "后端服务正在运行 (PID: $pid)"
        
        # 显示进程信息
        ps -p $pid -o pid,ppid,cmd,etime
    else
        log_info "后端服务未运行"
    fi
}

# 查看日志
view_logs() {
    local log_file="$PROJECT_ROOT/logs/backend.log"
    if [ -f "$log_file" ]; then
        log_info "显示后端日志 (按 Ctrl+C 退出):"
        tail -f "$log_file"
    else
        log_warning "日志文件不存在: $log_file"
    fi
}

# 完整部署
full_deploy() {
    log_info "开始完整部署..."
    
    # 创建logs目录
    mkdir -p "$PROJECT_ROOT/logs"
    
    # 构建前端
    build_frontend
    
    # 重启后端
    restart_backend
    
    log_success "部署完成！"
    log_info "前端构建文件位于: $FRONTEND_DIR/dist"
    log_info "后端服务已启动，日志文件: $PROJECT_ROOT/logs/backend.log"
}

# 显示帮助信息
show_help() {
    echo "量化交易系统部署和服务管理脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  build          构建前端"
    echo "  start          启动后端服务"
    echo "  stop           停止后端服务"
    echo "  restart        重启后端服务"
    echo "  status         查看后端服务状态"
    echo "  logs           查看后端日志"
    echo "  deploy         完整部署 (构建前端 + 重启后端)"
    echo "  help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 deploy      # 完整部署"
    echo "  $0 build       # 仅构建前端"
    echo "  $0 restart     # 重启后端服务"
    echo "  $0 status      # 查看服务状态"
}

# 主函数
main() {
    case "${1:-help}" in
        "build")
            build_frontend
            ;;
        "start")
            start_backend
            ;;
        "stop")
            stop_backend
            ;;
        "restart")
            restart_backend
            ;;
        "status")
            status_backend
            ;;
        "logs")
            view_logs
            ;;
        "deploy")
            full_deploy
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"