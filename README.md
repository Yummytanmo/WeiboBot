# WeiboBot Unified Project

这是一个集成了 Agent 对话和 Workflow 工作流自动化的统一平台。

## 项目结构

- `unified_server.py`: 统一的后端服务器入口，同时托管 API 和前端静态资源。
- `web/`: 基于 React + Vite + Tailwind CSS 的现代化前端项目。
- `agent/`: Agent 相关的后端逻辑和 API。
- `workflow/`: Workflow 相关的后端逻辑和 API。
- `weibo_service/`: 微博底层服务接口。

## 快速开始

### 1. 环境准备

确保已安装：
- Python 3.8+
- Node.js 16+

### 2. 安装依赖

**后端依赖**：
```bash
pip install -r requirements.txt
```

**前端依赖**：
```bash
cd web
npm install
```

### 3. 构建前端

在使用前，需要编译前端资源：
```bash
cd web
npm run build
```
构建完成后，静态文件会生成在 `web/dist` 目录中。

### 4. 启动服务

回到项目根目录，启动统一服务器：
```bash
python unified_server.py
```

服务启动后，访问：
- **Web 界面**: [http://localhost:8000](http://localhost:8000)
- **Agent API 文档**: [http://localhost:8000/api/agent/docs](http://localhost:8000/api/agent/docs)
- **Workflow API 文档**: [http://localhost:8000/api/workflow/docs](http://localhost:8000/api/workflow/docs)

## 功能说明

### Agent 对话
- 支持流式对话。
- 可配置模型参数（Temperature, Model 等）。
- 会话管理（创建、重置、历史记录）。

### Workflow 工作流
- **Browse**: 浏览互动工作流。
- **Post Review**: 发帖审核工作流。
- **Daily**: 日常活跃工作流。
- 实时查看运行日志和状态。

## 开发模式

如果需要修改前端代码并实时预览：

1. 启动后端：
   ```bash
   python unified_server.py
   ```
2. 启动前端开发服务器：
   ```bash
   cd web
   npm run dev
   ```
3. 访问 `http://localhost:5173` 进行开发调试。
