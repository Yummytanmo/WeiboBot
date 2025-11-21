import json
import os
import sys
from typing import Any, Dict, List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator

if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(CURRENT_DIR)
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)
    from agent.weibo_tools import (  # noqa: E402
        WeiboActionTool,
        WeiboGetStateTool,
        WeiboServiceToolkit,
    )
    from weibo_service.accounts import account_list  # type: ignore  # noqa: E402
else:
    from agent.weibo_tools import WeiboActionTool, WeiboGetStateTool, WeiboServiceToolkit
    from weibo_service.accounts import account_list  # type: ignore


PERSONA = "职业：科技/AI 领域博主；风格：理性、专业、乐观；语气：简洁、有观点、有行动号召。"


class InteractionDecision(BaseModel):
    target_object: str = Field(..., description="目标对象 uid/weibo_id")
    action_type: str = Field(..., description="like/comment/repost/skip")
    action_content: Optional[str] = Field(None, description="评论或转发时的文本")
    reason: str = Field(..., description="做出该动作的简要理由")

    @field_validator("action_type")
    def _normalize_action_type(cls, value: str) -> str:
        value_lower = value.lower()
        if value_lower not in {"like", "comment", "repost", "skip"}:
            raise ValueError("action_type 必须是 like/comment/repost/skip")
        return value_lower


class InteractionPlan(BaseModel):
    decisions: List[InteractionDecision]


def _build_llm(model: str = "gpt-4o-mini", temperature: float = 0.3) -> ChatOpenAI:
    api_key = os.getenv("YUNWU_API_KEY")
    base_url = os.getenv("YUNWU_BASE_URL")
    if not api_key or not base_url:
        raise RuntimeError("请先设置 YUNWU_API_KEY 与 YUNWU_BASE_URL 环境变量。")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
        timeout=600,
    )


def _summarize_feed(llm: ChatOpenAI, feed_data: Dict[str, Any]) -> str:
    """
    生成浏览前的快照，帮助 LLM 聚焦可互动的贴文。
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "压缩微博流，挑出亮点、争议点以及和科技/AI 相关的机会点。"),
            ("human", "微博流 JSON：\n{data}"),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"data": json.dumps(feed_data, ensure_ascii=False)})


def _collect_object_map(feed_data: Dict[str, Any]) -> Dict[str, str]:
    """
    构建 weibo_id -> uid/weibo_id 的映射，兜底补全目标对象。
    """
    mapping: Dict[str, str] = {}
    for bucket in ("post_from_followings", "post_from_recommends"):
        for item in feed_data.get(bucket, []):
            uid = item.get("uid") or item.get("account_id")
            weibo_id = item.get("weibo_id")
            if uid and weibo_id:
                key = str(weibo_id)
                mapping[key] = f"{uid}/{weibo_id}"
                mapping[f"{uid}/{weibo_id}"] = f"{uid}/{weibo_id}"
    return mapping


def _decide_interactions(
    llm: ChatOpenAI, feed_data: Dict[str, Any], persona: str, max_actions: int
) -> List[InteractionDecision]:
    """
    针对每条贴文给出互动决策：点赞/评论/转发/跳过。
    """
    decision_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你负责浏览微博流，结合人设挑选高价值互动。最多执行 {max_actions} 个实际动作；"
                "与人设或质量不匹配的内容请 skip。评论/转发要口吻自然、有观点且不超过 80 字。",
            ),
            (
                "human",
                "人设：{persona}\n微博流数据：{data}\n请输出结构化决策，target_object 必填 uid/weibo_id。",
            ),
        ]
    )
    chain = decision_prompt | llm.with_structured_output(InteractionPlan)
    result = chain.invoke(
        {
            "persona": persona,
            "data": json.dumps(feed_data, ensure_ascii=False),
            "max_actions": max_actions,
        }
    )
    return result.decisions


def run_browse_interaction_workflow(
    agent_id: str,
    model: str = "gpt-5",
    n_following: int = 5,
    n_recommend: int = 5,
    max_actions: int = 5,
    tool_timeout: float = 600.0,
) -> Dict[str, Any]:
    """
    浏览微博流，生成互动决策并执行点赞/评论/转发。

    流程：
      1) 拉取关注/推荐流；
      2) 摘要热点，辅助决策；
      3) 生成互动决策，最多 max_actions 个实际动作；
      4) 调用后台执行对应动作。
    """
    llm = _build_llm(model=model)
    toolkit = WeiboServiceToolkit(account_list, timeout=tool_timeout)
    state_tool = WeiboGetStateTool(toolkit.base_url, toolkit.timeout)
    action_tool = WeiboActionTool(toolkit.base_url, toolkit.timeout)

    print(">>> 拉取微博流用于浏览决策...")
    raw_state = state_tool.invoke(
        {
            "agent_id": agent_id,
            "n_following": n_following,
            "n_recommend": n_recommend,
        }
    )
    feed_data = json.loads(raw_state)
    object_map = _collect_object_map(feed_data)

    print(">>> 生成热点摘要...")
    feed_summary = _summarize_feed(llm, feed_data)
    print(feed_summary)

    print("\n>>> 生成互动决策...")
    decisions = _decide_interactions(llm, feed_data, PERSONA, max_actions=max_actions)
    print(json.dumps([d.model_dump() for d in decisions], ensure_ascii=False, indent=2))

    responses: List[Dict[str, Any]] = []
    executed_count = 0
    for decision in decisions:
        if decision.action_type == "skip":
            continue
        if executed_count >= max_actions:
            break

        target_object = decision.target_object
        if "/" not in target_object:
            target_object = object_map.get(target_object, target_object)
        if "/" not in target_object:
            print(f"跳过 {decision.action_type}，未找到完整目标：{decision.target_object}")
            continue

        payload = {
            "agent_id": agent_id,
            "action_type": decision.action_type,
            "action_content": decision.action_content,
            "target_object": target_object,
        }
        resp_raw = action_tool.invoke(payload)
        responses.append({"decision": decision.model_dump(), "response": resp_raw})
        executed_count += 1
        print(f"已执行 {decision.action_type} -> {target_object}，响应：{resp_raw}")

    return {
        "feed": feed_data,
        "summary": feed_summary,
        "decisions": [d.model_dump() for d in decisions],
        "responses": responses,
    }


if __name__ == "__main__":
    default_agent_id = str(account_list[0]["account_id"]) if account_list else ""
    run_browse_interaction_workflow(agent_id=default_agent_id)
