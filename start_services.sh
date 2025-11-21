#!/bin/bash
# 启动WeiboBot完整服务

echo "🚀 启动WeiboBot服务..."
echo ""

# 检查是否在项目根目录
if [ ! -f "unified_server.py" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  警告: 未检测到虚拟环境"
    echo "建议先激活虚拟环境: conda activate langchain"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 启动后端服务
echo "📡 启动后端服务 (unified_server.py)..."
python unified_server.py &
BACKEND_PID=$!
echo "✓ 后端服务已启动 (PID: $BACKEND_PID)"
echo ""

# 等待后端启动
sleep 3

# 启动前端服务
echo "🎨 启动前端服务..."
cd web
npm run dev &
FRONTEND_PID=$!
echo "✓ 前端服务已启动 (PID: $FRONTEND_PID)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 服务启动成功！"
echo ""
echo "🌐 前端地址: http://localhost:5173"
echo "   - Agent Chat: http://localhost:5173/agent"
echo "   - Workflows: http://localhost:5173/workflow"
echo "   - Workflow Builder: http://localhost:5173/workflow-builder"
echo ""
echo "📡 后端API: http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
wait
