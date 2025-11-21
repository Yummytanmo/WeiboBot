"""
Workflow Frontend API - 基于LangGraph
提供workflow执行和管理的HTTP接口
"""
import threading
from contextlib import redirect_stdout
from datetime import datetime
from enum import Enum
from io import StringIO
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 导入LangGraph workflow系统
from workflow import (
    create_daily_schedule_graph,
    create_post_review_graph,
    create_browse_interaction_graph,
    create_daily_agent_graph,
    run_graph,
    LANGGRAPH_AVAILABLE,
)

app = FastAPI(title="Workflow Frontend API")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WorkflowType(str, Enum):
    """Workflow类型枚举"""
    DAILY_SCHEDULE = "daily_schedule"
    POST_REVIEW = "post_review"
    BROWSE_INTERACTION = "browse_interaction"
    DAILY_AGENT = "daily_agent"


class WorkflowRequest(BaseModel):
    """Workflow执行请求"""
    workflow: WorkflowType
    agent_id: str
    # 通用参数
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.3
    tool_timeout: float = 600.0
    # Post相关
    current_post_topic: Optional[str] = None
    current_post_notes: Optional[str] = None
    max_review_rounds: int = 2
    auto_post: bool = True
    # Schedule相关
    min_slots: int = 3
    max_slots: int = 5
    start_time: str = "09:00"
    end_time: str = "22:00"
    # Browse相关
    max_interactions: int = 5


class WorkflowStatus(str, Enum):
    """Workflow状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeStatus(BaseModel):
    """节点执行状态"""
    id: str
    label: str
    status: WorkflowStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None


class WorkflowRun(BaseModel):
    """Workflow执行记录"""
    id: str
    workflow: WorkflowType
    status: WorkflowStatus
    params: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    logs: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    current_node: Optional[str] = None
    # 执行图数据
    nodes: List[NodeStatus] = []
    edges: List[Dict[str, str]] = []
    
    class Config:
        arbitrary_types_allowed = True


ICON_MAP = {
    "fetch_feed": "📥",
    "summarize_trending": "📊",
    "generate_schedule": "📅",
    "compose": "✍️",
    "compose_post": "✍️",
    "review": "👁️",
    "review_post": "👁️",
    "post": "🚀",
    "post_weibo": "🚀",
    "decide": "🤔",
    "decide_interactions": "🤔",
    "execute": "💬",
    "execute_interactions": "💬",
}


# 存储workflow运行记录
_runs: Dict[str, WorkflowRun] = {}
_runs_lock = threading.Lock()


def _get_workflow_graph(workflow_type: WorkflowType):
    """根据类型获取workflow图"""
    if not LANGGRAPH_AVAILABLE:
        raise HTTPException(status_code=500, detail="LangGraph未安装，请运行: pip install langgraph")
    
    graph_creators = {
        WorkflowType.DAILY_SCHEDULE: create_daily_schedule_graph,
        WorkflowType.POST_REVIEW: create_post_review_graph,
        WorkflowType.BROWSE_INTERACTION: create_browse_interaction_graph,
        WorkflowType.DAILY_AGENT: create_daily_agent_graph,
    }
    
    creator = graph_creators.get(workflow_type)
    if not creator:
        raise HTTPException(status_code=400, detail=f"未知的workflow类型: {workflow_type}")
    
    return creator()


def _massage_node(node_id: Any, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """构造前端节点描述"""
    text_id = str(node_id)
    label = (data or {}).get("label") or (data or {}).get("name") or text_id.replace("_", " ").title()
    return {
        "id": text_id,
        "label": label,
        "icon": ICON_MAP.get(text_id),
    }


def _extract_graph_structure(graph) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    从LangGraph编译后的graph中提取节点/边结构。
    仅依赖通用的 get_graph() 方法，尽量不假定内部实现。
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 优先使用 get_graph() 提供的 networkx 图
    if hasattr(graph, "get_graph"):
        nx_graph = graph.get_graph()
        # 提取节点
        try:
            node_view = getattr(nx_graph, "nodes", None)
            node_iter = node_view(data=True) if callable(node_view) else getattr(node_view, "data", lambda data=True: [])(data=True)
            for node_id, data in list(node_iter):
                node_data = data if isinstance(data, dict) else {}
                nodes.append(_massage_node(node_id, node_data))
        except Exception:
            pass
        # 提取边
        try:
            is_multi = callable(getattr(nx_graph, "is_multigraph", None)) and nx_graph.is_multigraph()
            edge_view = getattr(nx_graph, "edges", None)
            edge_iter = (
                edge_view(keys=True, data=True) if (callable(edge_view) and is_multi) else
                edge_view(data=True) if callable(edge_view) else
                getattr(edge_view, "data", lambda data=True: [])(data=True)
            )
            for edge in list(edge_iter):
                try:
                    if is_multi:
                        source, target, _key, attr = edge
                    else:
                        source, target, attr = edge
                except Exception:
                    continue
                label = None
                if isinstance(attr, dict):
                    label = attr.get("label") or attr.get("condition") or attr.get("name")
                edges.append({
                    "id": f"{source}->{target}-{len(edges)}",
                    "source": str(source),
                    "target": str(target),
                    "label": label,
                })
        except Exception:
            pass

    # 如果未成功获取，尝试 fallback（空）
    if not nodes:
        return [], []
    return nodes, edges


def _get_workflow_graph_layout(workflow_type: WorkflowType) -> Dict[str, Any]:
    """
    获取workflow的节点和边布局。
    优先从LangGraph真实结构提取，无法提取时返回空节点/边，
    由前端执行自动布局。
    """
    try:
        graph = _get_workflow_graph(workflow_type)
        nodes, edges = _extract_graph_structure(graph)
        if nodes:
            return {"nodes": nodes, "edges": edges}
    except Exception as exc:
        # 捕获但不阻断，让前端有机会使用简易fallback
        print(f"⚠️ 无法提取workflow图结构: {exc}")

    # fallback：仅提供基本信息（前端会自动布局）
    fallbacks = {
        WorkflowType.DAILY_SCHEDULE: ["fetch_feed", "summarize_trending", "generate_schedule"],
        WorkflowType.POST_REVIEW: ["compose", "review", "post"],
        WorkflowType.BROWSE_INTERACTION: ["fetch_feed", "decide", "execute"],
        WorkflowType.DAILY_AGENT: [
            "fetch_feed", "summarize_trending", "generate_schedule",
            "compose_post", "review_post", "post_weibo",
            "decide_interactions", "execute_interactions",
        ],
    }
    node_ids = fallbacks.get(workflow_type, [])
    return {
        "nodes": [_massage_node(node_id) for node_id in node_ids],
        "edges": [],
    }


def _build_initial_state(request: WorkflowRequest) -> Dict[str, Any]:
    """构建初始状态"""
    return {
        "agent_id": request.agent_id,
        "llm_model": request.llm_model,
        "llm_temperature": request.llm_temperature,
        "tool_timeout": request.tool_timeout,
        "current_post_topic": request.current_post_topic,
        "current_post_notes": request.current_post_notes,
        "max_review_rounds": request.max_review_rounds,
        "auto_post": request.auto_post,
        "min_slots": request.min_slots,
        "max_slots": request.max_slots,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "max_interactions": request.max_interactions,
    }


def _execute_workflow(run_id: str, request: WorkflowRequest):
    """后台执行workflow"""
    with _runs_lock:
        run = _runs[run_id]
        run.status = WorkflowStatus.RUNNING
        run.started_at = datetime.utcnow()
    
    try:
        # 获取workflow图
        graph = _get_workflow_graph(request.workflow)
        
        # 构建初始状态
        initial_state = _build_initial_state(request)
        
        # 捕获日志
        log_stream = StringIO()
        with redirect_stdout(log_stream):
            # 执行workflow
            final_state = run_graph(graph, initial_state)
        
        # 更新结果
        with _runs_lock:
            run.status = WorkflowStatus.COMPLETED
            run.finished_at = datetime.utcnow()
            run.logs = log_stream.getvalue()
            run.result = final_state
            run.current_node = final_state.get("current_node")
    
    except Exception as e:
        with _runs_lock:
            run.status = WorkflowStatus.FAILED
            run.finished_at = datetime.utcnow()
            run.error = str(e)


@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "Workflow Frontend API",
        "langgraph_available": LANGGRAPH_AVAILABLE,
    }


@app.get("/graph/{workflow_type}")
async def get_workflow_graph_layout(workflow_type: WorkflowType):
    """获取workflow的节点和边布局"""
    return _get_workflow_graph_layout(workflow_type)


@app.post("/trigger")
async def trigger_workflow(request: WorkflowRequest):
    """触发workflow执行"""
    # 创建运行记录
    run_id = str(uuid4())
    run = WorkflowRun(
        id=run_id,
        workflow=request.workflow,
        status=WorkflowStatus.PENDING,
        params=request.dict(),
        created_at=datetime.utcnow(),
    )
    
    with _runs_lock:
        _runs[run_id] = run
    
    # 后台执行
    thread = threading.Thread(target=_execute_workflow, args=(run_id, request))
    thread.daemon = True
    thread.start()
    
    return {"run_id": run_id, "status": "triggered"}


@app.get("/runs")
async def list_runs():
    """获取所有运行记录"""
    with _runs_lock:
        return {
            "runs": [
                {
                    "id": run.id,
                    "workflow": run.workflow,
                    "status": run.status,
                    "created_at": run.created_at.isoformat(),
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                }
                for run in _runs.values()
            ]
        }


@app.get("/run/{run_id}")
async def get_run(run_id: str):
    """获取运行详情"""
    with _runs_lock:
        run = _runs.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        return run.dict()


@app.delete("/run/{run_id}")
async def delete_run(run_id: str):
    """删除运行记录"""
    with _runs_lock:
        if run_id not in _runs:
            raise HTTPException(status_code=404, detail="Run not found")
        del _runs[run_id]
    
    return {"status": "deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
