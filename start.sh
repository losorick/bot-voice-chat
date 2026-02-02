#!/bin/bash

# Bot Voice Chat - 服务启动脚本
# 用法: ./start.sh

set -e

# 获取脚本所在目录作为项目根
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# 配置
BACKEND_DIR="$PROJECT_ROOT/code/backend"
FRONTEND_DIR="$PROJECT_ROOT/code/frontend"
BACKEND_PORT=5002
FRONTEND_PORT=5173

echo "🚀 启动 Bot Voice Chat 服务..."

# 停止现有服务
echo "🛑 停止现有服务..."
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "node.*vite" 2>/dev/null || true
sleep 1

# 启动后端
echo "📦 启动后端服务..."
cd "$BACKEND_DIR"
echo "   工作目录: $(pwd)"
if [ -f .env ]; then
    echo "   .env: 已找到"
    set -a && source .env && set +a
else
    echo "   .env: 未找到 (将依赖 main.py 内置加载)"
fi
source bot-voice-env/bin/activate
nohup python main.py --server --port $BACKEND_PORT > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 3

# 检查后端状态
if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
    echo "   ✅ 后端服务已启动: http://localhost:$BACKEND_PORT"
else
    echo "   ❌ 后端服务启动失败"
    tail -10 /tmp/backend.log
    exit 1
fi

# 启动前端
echo "🎨 启动前端服务..."
cd "$FRONTEND_DIR"
nohup npm run dev -- --port $FRONTEND_PORT > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   前端 PID: $FRONTEND_PID"

# 等待前端启动
sleep 5

# 检查前端状态
if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
    echo "   ✅ 前端服务已启动: http://localhost:$FRONTEND_PORT"
else
    echo "   ⚠️ 前端服务可能还在启动中..."
fi

echo ""
echo "========================================"
echo "✅ 服务启动完成！"
echo ""
echo "   前端: http://localhost:$FRONTEND_PORT"
echo "   后端: http://localhost:$BACKEND_PORT"
echo "   健康检查: http://localhost:$BACKEND_PORT/health"
echo ""
echo "📝 日志查看:"
echo "   后端: tail -f /tmp/backend.log"
echo "   前端: tail -f /tmp/frontend.log"
echo ""
echo "🛑 停止服务:"
echo "   pkill -f 'python.*main.py'"
echo "   pkill -f 'vite'"
echo "========================================"
