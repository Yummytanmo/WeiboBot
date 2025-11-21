import json
import os
import sys
import threading
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain.agents import AgentExecutor
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field, validator

if __package__ in (None, ""):
    CURRENT_DIR = Path(__file__).resolve().parent
    PARENT_DIR = CURRENT_DIR.parent
    if str(PARENT_DIR) not in sys.path:
        sys.path.append(str(PARENT_DIR))
from agent.weibo_agent import create_weibo_langchain_agent  # noqa: E402
from weibo_service.accounts import account_list  # type: ignore  # noqa: E402


class SessionConfig(BaseModel):
    api_key: Optional[str] = Field(
        None,
        description="OpenAI / 兼容 API 的 key，留空时读取环境变量。",
    )
    base_url: Optional[str] = Field(
        None, description="OpenAI 兼容 API 的 base URL，留空时读取环境变量。"
    )
    model: str = Field(
        "gpt-4o-mini",
        description="模型名称，例如 gpt-4o-mini、gpt-4o-mini-1 或其它第三方模型。",
    )
    temperature: float = Field(
        0.2,
        ge=0.0,
        le=2.0,
        description="生成温度，范围 0~2，可控制创造性与稳定性。",
    )
    llm_timeout: float = Field(
        600.0,
        gt=0,
        description="LLM 请求超时时间（秒），默认 10 分钟。",
    )
    tool_timeout: float = Field(
        600.0,
        gt=0,
        description="微博后台工具调用超时时间（秒），默认 10 分钟。",
    )
    streaming: bool = Field(
        True,
        description="是否启用流式输出（需下游模型支持）。",
    )

    @validator("api_key", "base_url", pre=True)
    def _blank_to_none(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ChatPayload(BaseModel):
    session_id: str = Field(..., description="由 /api/session 返回的 session ID")
    message: str = Field(..., description="新的用户输入")


class ResetPayload(BaseModel):
    session_id: str


class AgentSession:
    def __init__(self, executor: AgentExecutor, streaming: bool):
        self.executor = executor
        self.chat_history: List[BaseMessage] = []
        self.streaming = streaming
        self.busy = threading.Lock()


STATIC_DIR = Path(__file__).resolve().parent / "static"
FRONTEND_FILE = STATIC_DIR / "weibo_agent.html"

app = FastAPI(title="Weibo Agent UI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_sessions: Dict[str, AgentSession] = {}
_session_lock = threading.Lock()


def _serialized_history(history: List[BaseMessage]) -> List[Dict[str, str]]:
    serialized: List[Dict[str, str]] = []
    for msg in history:
        role = "assistant"
        if isinstance(msg, HumanMessage):
            role = "user"
        elif not isinstance(msg, AIMessage):
            role = msg.__class__.__name__
        serialized.append(
            {
                "role": role,
                "content": msg.content if isinstance(msg.content, str) else str(msg.content),
            }
        )
    return serialized


def _serialize_steps(steps: Optional[List[Any]]) -> List[Dict[str, str]]:
    serialized: List[Dict[str, str]] = []
    if not steps:
        return serialized
    for item in steps:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        action, observation = item
        serialized.append(
            {
                "tool": getattr(action, "tool", "") or "",
                "input": str(getattr(action, "tool_input", "")),
                "log": getattr(action, "log", "") or "",
                "observation": str(observation),
            }
        )
    return serialized


class StreamingAgentCallbackHandler(BaseCallbackHandler):
    """Send LangChain streaming events to an in-memory queue for SSE."""

    def __init__(self, queue: "Queue[Dict[str, Any]]"):
        self.queue = queue

    def _emit(self, event_type: str, payload: Dict[str, Any]):
        self.queue.put({"type": event_type, "payload": payload})

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            return str(value)

    def on_llm_start(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        self._emit("status", {"state": "thinking"})

    def on_llm_new_token(self, token: str, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        if token:
            self._emit("token", {"content": token})

    def on_llm_end(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        self._emit("status", {"state": "thought_complete"})

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        run_id: Any,
        parent_run_id: Any = None,  # noqa: ANN401
        **kwargs: Any,
    ) -> None:
        tool_name = ""
        if isinstance(serialized, dict):
            tool_name = serialized.get("name") or serialized.get("tool") or ""
        elif isinstance(serialized, list) and serialized:
            tool_name = str(serialized[-1])
        payload = {
            "id": str(run_id),
            "tool": tool_name,
            "input": self._stringify(input_str),
        }
        self._emit("status", {"state": "executing", "tool": tool_name})
        self._emit("tool_start", payload)

    def on_tool_end(
        self,
        output: Any,
        run_id: Any,
        parent_run_id: Any = None,  # noqa: ANN401
        **kwargs: Any,
    ) -> None:
        payload = {
            "id": str(run_id),
            "tool": kwargs.get("name") or "",
            "output": self._stringify(output),
        }
        self._emit("tool_result", payload)

    def on_tool_error(
        self,
        error: Exception,
        run_id: Any,
        parent_run_id: Any = None,  # noqa: ANN401
        **kwargs: Any,
    ) -> None:
        payload = {
            "id": str(run_id),
            "tool": kwargs.get("name") or "",
            "error": str(error),
        }
        self._emit("tool_result", payload)


def _create_session(config: SessionConfig) -> AgentSession:
    executor = create_weibo_langchain_agent(
        account_list,
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        temperature=config.temperature,
        timeout=config.llm_timeout,
        tool_timeout=config.tool_timeout,
        streaming=config.streaming,
    )
    return AgentSession(executor, streaming=config.streaming)


def _get_session(session_id: str) -> AgentSession:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已失效。")
    return session


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    if not FRONTEND_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail="未找到前端页面，请确认 agent/static/weibo_agent.html 已生成。",
        )
    return HTMLResponse(FRONTEND_FILE.read_text(encoding="utf-8"))


@app.get("/api/config")
def get_config():
    sanitized_accounts = [{"account_id": acct.get("account_id")} for acct in account_list]
    return {
        "accounts": sanitized_accounts,
        "defaults": {
            "model": "gpt-4o-mini",
            "temperature": 0.2,
            "llm_timeout": 600,
            "tool_timeout": 600,
        },
    }


@app.post("/api/session")
def create_session(config: SessionConfig):
    try:
        session = _create_session(config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session_id = uuid4().hex
    with _session_lock:
        _sessions[session_id] = session
    return {
        "session_id": session_id,
        "history": _serialized_history(session.chat_history),
        "streaming": session.streaming,
    }


@app.post("/api/chat")
def chat(payload: ChatPayload):
    session = _get_session(payload.session_id)
    if session.streaming:
        raise HTTPException(status_code=400, detail="该会话启用了流式响应，请调用 /api/chat/stream。")
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="输入不能为空。")
    if not session.busy.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="当前会话正在执行上一条指令，请稍后再试。")
    try:
        result = session.executor.invoke(
            {
                "input": message,
                "chat_history": session.chat_history,
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        session.busy.release()

    output = result.get("output", "")
    session.chat_history.extend(
        [
            HumanMessage(content=message),
            AIMessage(content=output),
        ]
    )
    return {
        "response": {"role": "assistant", "content": output},
        "history": _serialized_history(session.chat_history),
        "steps": _serialize_steps(result.get("intermediate_steps")),
    }


@app.post("/api/chat/stream")
def chat_stream(payload: ChatPayload):
    session = _get_session(payload.session_id)
    if not session.streaming:
        raise HTTPException(status_code=400, detail="该会话未启用流式输出。")
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="输入不能为空。")
    if not session.busy.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="当前会话正在执行上一条指令，请稍后再试。")

    queue: "Queue[Dict[str, Any]]" = Queue()
    handler = StreamingAgentCallbackHandler(queue)

    def _worker():
        try:
            result = session.executor.invoke(
                {
                    "input": message,
                    "chat_history": session.chat_history,
                },
                config={"callbacks": [handler]},
            )
            queue.put({"type": "status", "payload": {"state": "finalizing"}})
            output = result.get("output", "")
            session.chat_history.extend(
                [
                    HumanMessage(content=message),
                    AIMessage(content=output),
                ]
            )
            queue.put(
                {
                    "type": "final",
                    "payload": {
                        "output": output,
                        "history": _serialized_history(session.chat_history),
                        "steps": _serialize_steps(result.get("intermediate_steps")),
                    },
                }
            )
        except Exception as exc:  # noqa: BLE001
            queue.put(
                {
                    "type": "error",
                    "payload": {"message": str(exc)},
                }
            )
        finally:
            session.busy.release()
            queue.put({"type": "done"})

    threading.Thread(target=_worker, daemon=True).start()

    def event_stream():
        while True:
            event = queue.get()
            if not event:
                continue
            if event["type"] == "done":
                break
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/json")


@app.post("/api/session/reset")
def reset_session(payload: ResetPayload):
    session = _get_session(payload.session_id)
    session.chat_history.clear()
    return {"history": _serialized_history(session.chat_history)}


@app.delete("/api/session/{session_id}")
def delete_session(session_id: str):
    with _session_lock:
        session = _sessions.pop(session_id, None)
    if not session:
        raise HTTPException(status_code=404, detail="会话已删除或不存在。")
    return {"success": True}


if __name__ == "__main__":
    if __package__ in (None, ""):
        from weibo_service.accounts import account_list as _account_list  # type: ignore  # noqa: F401
    import uvicorn

    host = os.getenv("WEIBO_AGENT_UI_HOST", "0.0.0.0")
    port = int(os.getenv("WEIBO_AGENT_UI_PORT", "18080"))
    uvicorn.run(app, host=host, port=port)
