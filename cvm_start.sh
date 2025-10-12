#!/bin/bash

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 切换到后端目录
cd src/backend

# 启动后端服务
python3.9 main.py