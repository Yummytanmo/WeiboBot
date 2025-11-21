"""
Workflow Frontend API - 基于LangGraph
提供workflow执行和管理的HTTP接口
"""
import threading
from contextlib import redirect_stdout
from datetime import datetime
from enum import Enum
from io import StringIO
from typing import Dict, List, Optional, Any
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
