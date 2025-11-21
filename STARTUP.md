# WeiboBot 服务启动指南

## 快速启动

### 方式1: 使用启动脚本（推荐）

```bash
./start_services.sh
```

这将自动启动：
- 后端服务 (unified_server.py)
- 前端服务 (npm run dev)

### 方式2: 手动启动

**终端1 - 启动后端:**
```bash
# 确保在项目根目录
conda activate langchain  # 或你的虚拟环境
python unified_server.py
```

**终端2 - 启动前端:**
```bash
cd web
npm run dev
```

## 访问地址

### 前端页面
- 🏠 主页: http://localhost:5173
- 💬 Agent Chat: http://localhost:5173/agent
- 📋 Workflows: http://localhost:5173/workflow
- 🔧 Workflow Builder: http://localhost:5173/workflow-builder

### 后端API
- 📡 API地址: http://localhost:8000
- 📖 API文档: http://localhost:8000/docs

## Workflow Builder使用

1. 访问 http://localhost:5173/workflow-builder
2. 从左侧节点库拖拽节点到画布
3. 连接节点构建workflow
4. 点击Save保存（查看控制台）
5. 点击Execute执行

## 环境要求

### 后端
- Python 3.8+
- 已安装依赖: `pip install -r requirements.txt`
- 环境变量:
  - `YUNWU_API_KEY`
  - `YUNWU_BASE_URL`

### 前端
- Node.js 16+
- 已安装依赖: `cd web && npm install`

## 故障排查

### 后端无法启动
```bash
# 检查依赖
pip list | grep langchain
pip list | grep langgraph

# 重新安装
pip install langchain langgraph langchain-openai
```

### 前端无法启动
```bash
cd web
# 清理并重新安装
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### ReactFlow相关错误
```bash
cd web
npm install reactflow
```

## 停止服务

### 使用脚本启动的
按 `Ctrl+C` 停止所有服务

### 手动启动的
在各自终端按 `Ctrl+C`
