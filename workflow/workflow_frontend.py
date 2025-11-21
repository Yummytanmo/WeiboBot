import io
import os
import sys
import threading
from contextlib import redirect_stdout
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator

if __package__ in (None, ""):
    CURRENT_DIR = Path(__file__).resolve().parent
    PARENT_DIR = CURRENT_DIR.parent
    if str(PARENT_DIR) not in sys.path:
        sys.path.append(str(PARENT_DIR))
    from workflow.browse_interaction_workflow import (  # type: ignore  # noqa: E402
        run_browse_interaction_workflow,
    )
    from workflow.daily_agent_workflow import run_daily_workflow  # type: ignore  # noqa: E402
    from workflow.post_review_workflow import run_post_review_workflow  # type: ignore  # noqa: E402
    from weibo_service.accounts import account_list  # type: ignore  # noqa: E402
else:
    from .browse_interaction_workflow import run_browse_interaction_workflow
    from .daily_agent_workflow import run_daily_workflow
    from .post_review_workflow import run_post_review_workflow
    from weibo_service.accounts import account_list  # type: ignore


class WorkflowType(str, Enum):
    BROWSE = "browse"
    POST_REVIEW = "post_review"
    DAILY = "daily"


WORKFLOW_DEFAULTS = {
    WorkflowType.BROWSE: {
        "model": "gpt-5",
        "n_following": 5,
        "n_recommend": 5,
        "max_actions": 5,
        "tool_timeout": 600,
    },
    WorkflowType.POST_REVIEW: {
        "model": "gpt-4o-mini",
        "tool_timeout": 600,
        "feedback_delay": 5,
        "max_review_rounds": 2,
    },
    WorkflowType.DAILY: {
        "model": "gpt-4o-mini",
        "min_slots": 3,
        "max_slots": 5,
        "n_following": 4,
        "n_recommend": 4,
        "tool_timeout": 600,
    },
}


class WorkflowRequest(BaseModel):
    workflow: WorkflowType = Field(..., description="workflow 类型")
    agent_id: str = Field(..., description="账号 ID")
    model: Optional[str] = Field(None, description="可选模型名，留空使用默认值")
    topic: Optional[str] = Field(None, description="post_review: 发帖主题")
    notes: Optional[str] = Field(None, description="post_review: 补充说明")
    trending: Optional[str] = Field(None, description="post_review: 热点摘要")
    feedback_delay: Optional[int] = Field(None, description="post_review: 拉取反馈前的等待秒数")
    max_review_rounds: Optional[int] = Field(None, description="post_review: 审核轮数上限")
    n_following: Optional[int] = Field(None, description="browse/daily: 关注流条数")
    n_recommend: Optional[int] = Field(None, description="browse/daily: 推荐流条数")
    max_actions: Optional[int] = Field(None, description="browse: 最大执行动作数")
    min_slots: Optional[int] = Field(None, description="daily: 最少时间槽")
    max_slots: Optional[int] = Field(None, description="daily: 最多时间槽")
    tool_timeout: Optional[float] = Field(None, description="工具调用超时时间（秒）")

    @validator(
        "feedback_delay",
        "max_review_rounds",
        "n_following",
        "n_recommend",
        "max_actions",
        "min_slots",
        "max_slots",
        pre=True,
    )
    def _empty_to_none(cls, value: Optional[Any]) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:  # noqa: BLE001
            raise ValueError("数值字段必须为整数") from exc

    @validator("tool_timeout", pre=True)
    def _normalize_timeout(cls, value: Optional[Any]) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        try:
            return float(value)
        except (TypeError, ValueError) as exc:  # noqa: BLE001
            raise ValueError("tool_timeout 必须为数字") from exc

    @validator("topic")
    def _topic_required(cls, value: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        if values.get("workflow") == WorkflowType.POST_REVIEW and not (value and value.strip()):
            raise ValueError("post_review workflow 需要 topic。")
        return value


class WorkflowRun:
    def __init__(self, run_id: str, workflow: WorkflowType, params: Dict[str, Any]):
        self.id = run_id
        self.workflow = workflow
        self.params = params
        self.status = "pending"
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.logs = ""
        self.result: Optional[Any] = None
        self.error: Optional[str] = None

    def to_dict(self, brief: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "workflow": self.workflow.value,
            "status": self.status,
            "params": self.params,
            "created_at": self.created_at.isoformat() + "Z",
            "started_at": self.started_at.isoformat() + "Z" if self.started_at else None,
            "finished_at": self.finished_at.isoformat() + "Z" if self.finished_at else None,
        }
        if not brief:
            data["logs"] = self.logs
            data["result"] = self.result
            data["error"] = self.error
        return data


STATIC_DIR = Path(__file__).resolve().parent / "static"
FRONTEND_FILE = STATIC_DIR / "workflow_console.html"

app = FastAPI(title="Workflow UI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_runs: Dict[str, WorkflowRun] = {}
_runs_lock = threading.Lock()


def _default_value(workflow: WorkflowType, key: str) -> Any:
    defaults = WORKFLOW_DEFAULTS.get(workflow, {})
    return defaults.get(key)


def _execute_workflow(run: WorkflowRun, payload: WorkflowRequest) -> None:
    run.started_at = datetime.utcnow()
    run.status = "running"
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            if payload.workflow == WorkflowType.BROWSE:
                run.result = run_browse_interaction_workflow(
                    agent_id=payload.agent_id,
                    model=payload.model or _default_value(WorkflowType.BROWSE, "model"),
                    n_following=payload.n_following or _default_value(WorkflowType.BROWSE, "n_following"),
                    n_recommend=payload.n_recommend or _default_value(WorkflowType.BROWSE, "n_recommend"),
                    max_actions=payload.max_actions or _default_value(WorkflowType.BROWSE, "max_actions"),
                    tool_timeout=payload.tool_timeout or _default_value(WorkflowType.BROWSE, "tool_timeout"),
                )
            elif payload.workflow == WorkflowType.POST_REVIEW:
                run.result = run_post_review_workflow(
                    agent_id=payload.agent_id,
                    topic=payload.topic or "",
                    notes=payload.notes,
                    trending=payload.trending,
                    model=payload.model or _default_value(WorkflowType.POST_REVIEW, "model"),
                    tool_timeout=payload.tool_timeout or _default_value(WorkflowType.POST_REVIEW, "tool_timeout"),
                    feedback_delay=payload.feedback_delay
                    if payload.feedback_delay is not None
                    else _default_value(WorkflowType.POST_REVIEW, "feedback_delay"),
                    max_review_rounds=payload.max_review_rounds
                    or _default_value(WorkflowType.POST_REVIEW, "max_review_rounds"),
                )
            else:
                run.result = run_daily_workflow(
                    agent_id=payload.agent_id,
                    model=payload.model or _default_value(WorkflowType.DAILY, "model"),
                    min_slots=payload.min_slots or _default_value(WorkflowType.DAILY, "min_slots"),
                    max_slots=payload.max_slots or _default_value(WorkflowType.DAILY, "max_slots"),
                    n_following=payload.n_following or _default_value(WorkflowType.DAILY, "n_following"),
                    n_recommend=payload.n_recommend or _default_value(WorkflowType.DAILY, "n_recommend"),
                    tool_timeout=payload.tool_timeout or _default_value(WorkflowType.DAILY, "tool_timeout"),
                )
        run.status = "success"
        if run.result is None:
            run.result = {"message": "workflow 执行完成（无显式返回值）"}
    except Exception as exc:  # noqa: BLE001
        run.status = "error"
        run.error = str(exc)
    finally:
        run.finished_at = datetime.utcnow()
        run.logs = buffer.getvalue()


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    if not FRONTEND_FILE.exists():
        raise HTTPException(status_code=500, detail="未找到前端页面，请确认 workflow/static/workflow_console.html 已生成。")
    return HTMLResponse(FRONTEND_FILE.read_text(encoding="utf-8"))


@app.get("/api/workflows/config")
def get_config():
    sanitized_accounts = [{"account_id": acct.get("account_id")} for acct in account_list]
    defaults = {key.value: value for key, value in WORKFLOW_DEFAULTS.items()}
    return {
        "accounts": sanitized_accounts,
        "defaults": defaults,
    }


@app.post("/api/workflows/run")
def trigger_workflow(payload: WorkflowRequest):
    run_id = uuid4().hex
    params = payload.dict()
    run = WorkflowRun(run_id, payload.workflow, params)
    with _runs_lock:
        _runs[run_id] = run
    thread = threading.Thread(target=_execute_workflow, args=(run, payload), daemon=True)
    thread.start()
    return {"run_id": run_id, "status": run.status}


@app.get("/api/workflows/run/{run_id}")
def get_run(run_id: str):
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_id 不存在或已过期。")
    return run.to_dict()


@app.get("/api/workflows")
def list_runs():
    with _runs_lock:
        runs = list(_runs.values())
    runs.sort(key=lambda x: x.created_at, reverse=True)
    return {"runs": [r.to_dict(brief=True) for r in runs[:20]]}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("WORKFLOW_UI_HOST", "127.0.0.1")
    port = int(os.getenv("WORKFLOW_UI_PORT", "18081"))
    uvicorn.run(app, host=host, port=port)
