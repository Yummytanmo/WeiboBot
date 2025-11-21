import json
import os
from typing import Any, Dict, List, Optional

import requests
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class _RemoteBaseTool(BaseTool):
    base_url: str
    timeout: float = 30.0

    def __init__(self, base_url: str, timeout: float = 30.0):
        super().__init__(base_url=base_url.rstrip("/"), timeout=timeout)

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Unexpected response: {data}")
        if data.get("success") is False:
            raise ValueError(json.dumps(data, ensure_ascii=False))
        return data


class _GetStateInput(BaseModel):
    agent_id: str = Field(..., description="账号 ID")
    n_following: int = Field(2, description="首页关注流返回条数")
    n_recommend: int = Field(2, description="热门/推荐返回条数")


class WeiboGetStateTool(_RemoteBaseTool):
    name: str = "weibo_get_state"
    description: str = "通过后台服务获取关注流与热门流内容。"
    args_schema: type[_GetStateInput] = _GetStateInput

    def _run(self, agent_id: str, n_following: int = 2, n_recommend: int = 2) -> str:
        data = self._post_json(
            "/state",
            {
                "agent_id": agent_id,
                "n_following": n_following,
                "n_recommend": n_recommend,
            },
        )
        return json.dumps(data.get("data"), ensure_ascii=False)

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("weibo_get_state 不支持异步。")


class _ActionInput(BaseModel):
    agent_id: str = Field(..., description="账号 ID")
    action_type: str = Field(..., description="post/repost/comment/like/follow/unfollow")
    action_content: Optional[str] = Field(None, description="操作文本内容，可选")
    target_object: Optional[str] = Field(
        None,
        description="目标对象，repost/comment/like 为 uid/weibo_id，关注类为 uid",
    )


class WeiboActionTool(_RemoteBaseTool):
    name: str = "weibo_action"
    description: str = "调用后台执行发帖、转发、评论、点赞、关注、取关等动作。"
    args_schema: type[_ActionInput] = _ActionInput

    def _run(
        self,
        agent_id: str,
        action_type: str,
        action_content: Optional[str] = None,
        target_object: Optional[str] = None,
    ) -> str:
        data = self._post_json(
            "/action",
            {
                "agent_id": agent_id,
                "action_type": action_type,
                "action_content": action_content,
                "target_object": target_object,
            },
        )
        return json.dumps(data, ensure_ascii=False)

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("weibo_action 不支持异步。")


class _FeedbackInput(BaseModel):
    agent_id: str = Field(..., description="账号 ID")
    weibo_id: Optional[str] = Field(
        None,
        description="微博 ID，可选。提供时返回互动数据，缺省时返回粉丝变化。",
    )


class WeiboFeedbackTool(_RemoteBaseTool):
    name: str = "weibo_get_feedback"
    description: str = "通过后台获取粉丝变化或单条微博互动反馈。"
    args_schema: type[_FeedbackInput] = _FeedbackInput

    def _run(self, agent_id: str, weibo_id: Optional[str] = None) -> str:
        data = self._post_json(
            "/feedback",
            {
                "agent_id": agent_id,
                "weibo_id": weibo_id,
            },
        )
        return json.dumps(data.get("data"), ensure_ascii=False)

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("weibo_get_feedback 不支持异步。")


class _RecordInput(BaseModel):
    object_id: str = Field(..., description="微博标识，格式 uid/weibo_id")


class WeiboRecordTool(_RemoteBaseTool):
    name: str = "weibo_get_record"
    description: str = "通过后台查询任意微博的详细内容。"
    args_schema: type[_RecordInput] = _RecordInput

    def _run(self, object_id: str) -> str:
        data = self._post_json("/record", {"object_id": object_id})
        return json.dumps(data.get("data"), ensure_ascii=False)

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("weibo_get_record 不支持异步。")


class WeiboServiceToolkit:
    """
    返回一组调用后台服务的 LangChain 工具。

    参数与旧版本保持兼容：可以继续传入 account_list（将被忽略），
    但现在工具会通过 HTTP 调用独立的微博后台服务。
    """

    def __init__(
        self,
        account_list: Optional[List[Dict[str, Any]]] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = (
            base_url
            or os.getenv("WEIBO_BACKEND_URL")
            or "http://127.0.0.1:11122"
        ).rstrip("/")
        self.timeout = timeout
        # account_list 保留以兼容旧代码，实际调用由后台完成
        self.account_list = account_list or []

    def get_tools(self) -> List[BaseTool]:
        return [
            WeiboGetStateTool(self.base_url, self.timeout),
            WeiboActionTool(self.base_url, self.timeout),
            WeiboFeedbackTool(self.base_url, self.timeout),
            WeiboRecordTool(self.base_url, self.timeout),
        ]
