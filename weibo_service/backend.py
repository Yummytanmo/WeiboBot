import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(CURRENT_DIR)
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)
    from WeiboBots import WeiboBots  # type: ignore
else:
    from .WeiboBots import WeiboBots


def _setup_logger() -> logging.Logger:
    """
    Configure a shared logger for backend runtime and request tracing.

    - File path can be overridden by WEIBO_BACKEND_LOG (default: ./weibo_backend.log).
    - Level can be overridden by WEIBO_BACKEND_LOG_LEVEL (default: INFO).
    """
    logger = logging.getLogger("weibo_service.backend")
    if logger.handlers:
        return logger

    level_name = os.getenv("WEIBO_BACKEND_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    log_path = os.getenv("WEIBO_BACKEND_LOG", os.path.join(os.getcwd(), "weibo_backend.log"))
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    try:
        file_handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("日志文件创建失败，fallback 到控制台日志: %s", exc)

    logger.propagate = False
    return logger


LOGGER = _setup_logger()


def _normalize_agent_id(agent_id: Any) -> Any:
    if isinstance(agent_id, str) and agent_id.isdigit():
        try:
            return int(agent_id)
        except ValueError:
            return agent_id
    return agent_id


class StatePayload(BaseModel):
    agent_id: str = Field(..., description="账号 ID")
    n_following: int = Field(3, description="关注流之间返回条数")
    n_recommend: int = Field(3, description="热门/推荐条数")


class ActionPayload(BaseModel):
    agent_id: str = Field(..., description="账号 ID")
    action_type: str = Field(..., description="post/repost/comment/like/follow/unfollow")
    action_content: Optional[str] = Field(None, description="文本内容，可选")
    target_object: Optional[str] = Field(
        None,
        description="目标 uid 或 uid/weibo_id",
    )


class FeedbackPayload(BaseModel):
    agent_id: str = Field(..., description="账号 ID")
    weibo_id: Optional[str] = Field(
        None,
        description="微博 ID，可选",
    )


class RecordPayload(BaseModel):
    object_id: str = Field(..., description="微博标识，格式 uid/weibo_id")


def create_app(account_list: List[Dict[str, Any]]) -> FastAPI:
    if not account_list:
        raise ValueError("account_list cannot be empty.")

    bots = WeiboBots(account_list)
    LOGGER.info("Backend initialized with %d accounts: %s", len(account_list), [acct["account_id"] for acct in account_list])

    app = FastAPI(title="Weibo Service Backend", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request, call_next):
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            LOGGER.exception("Request failed: %s %s -> %s", request.method, request.url.path, exc)
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            LOGGER.info("HTTP %s %s -> %s (%.1f ms)", request.method, request.url.path, status_code, duration_ms)

    @app.get("/health")
    def health():
        return {"status": "ok", "accounts": [acct["account_id"] for acct in account_list]}

    @app.post("/state")
    def get_state(payload: StatePayload):
        try:
            agent_id = _normalize_agent_id(payload.agent_id)
            LOGGER.info("Get state agent_id=%s following=%s recommend=%s", agent_id, payload.n_following, payload.n_recommend)
            result = bots.get_state(
                agent_id,
                n_following=payload.n_following,
                n_recommend=payload.n_recommend,
            )
            if result is None:
                raise HTTPException(status_code=404, detail="无法获取动态")
            LOGGER.debug("State result keys: %s", list(result.keys()))
            return {"success": True, "data": result}
        except HTTPException:
            raise
        except Exception as exc:
            LOGGER.exception("Get state failed for agent_id=%s", payload.agent_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/action")
    def do_action(payload: ActionPayload):
        agent_id = _normalize_agent_id(payload.agent_id)
        action = {
            "agent_id": agent_id,
            "type": payload.action_type,
            "action_content": payload.action_content,
            "object": payload.target_object,
        }
        try:
            LOGGER.info("Do action %s", action)
            result = bots.update_state(action)
            return {"success": bool(result), "data": result, "action": action}
        except Exception as exc:
            LOGGER.exception("Action failed: %s", action)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/feedback")
    def get_feedback(payload: FeedbackPayload):
        try:
            agent_id = _normalize_agent_id(payload.agent_id)
            LOGGER.info("Get feedback agent_id=%s weibo_id=%s", agent_id, payload.weibo_id)
            result = bots.get_feedback(agent_id, weibo_id=payload.weibo_id)
            if result is None:
                raise HTTPException(status_code=404, detail="未获取到反馈")
            return {"success": True, "data": result}
        except HTTPException:
            raise
        except Exception as exc:
            LOGGER.exception("Get feedback failed agent_id=%s weibo_id=%s", payload.agent_id, payload.weibo_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/record")
    def get_record(payload: RecordPayload):
        try:
            LOGGER.info("Get record object_id=%s", payload.object_id)
            result = bots.get_record(payload.object_id)
            if result is None:
                raise HTTPException(status_code=404, detail="未找到微博")
            return {"success": True, "data": result}
        except HTTPException:
            raise
        except Exception as exc:
            LOGGER.exception("Get record failed object_id=%s", payload.object_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app


if __name__ == "__main__":
    if __package__ in (None, ""):
        from accounts import account_list  # type: ignore
    else:
        from .accounts import account_list
    import uvicorn

    app = create_app(account_list)
    host = os.getenv("WEIBO_BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("WEIBO_BACKEND_PORT", "11122"))
    uvicorn.run(app, host=host, port=port)
