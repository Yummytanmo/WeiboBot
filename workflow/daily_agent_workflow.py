import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator

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


class PlanItem(BaseModel):
    time: str = Field(..., description="今日计划的时间点，如 10:00、15:30 或 上午/下午 均可。")
    action: str = Field(..., description="post 或 browse")
    topic: Optional[str] = Field(None, description="当 action=post 时的主题或角度")
    notes: Optional[str] = Field(None, description="补充说明/素材来源/互动目标")

    @validator("action")
    def _normalize_action(cls, value: str) -> str:
        value_lower = value.lower()
        if value_lower not in {"post", "browse"}:
            raise ValueError("action 必须是 post 或 browse")
        return value_lower


class DailyPlan(BaseModel):
    date: str = Field(..., description="计划生成日期 YYYY-MM-DD")
    items: List[PlanItem]

    @validator("date", pre=True)
    def _default_date(cls, value: Optional[str]) -> str:
        return value or datetime.now().strftime("%Y-%m-%d")


class BrowseDecision(BaseModel):
    target_object: str = Field(..., description="目标对象 uid/weibo_id")
    action_type: str = Field(..., description="like/comment/repost/skip")
    action_content: Optional[str] = Field(None, description="评论或转发时的文本，其他操作可为空")

    @validator("action_type")
    def _normalize_action_type(cls, value: str) -> str:
        value_lower = value.lower()
        if value_lower not in {"like", "comment", "repost", "skip"}:
            raise ValueError("action_type 必须是 like/comment/repost/skip")
        return value_lower


class BrowseDecisionList(BaseModel):
    decisions: List[BrowseDecision]


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
        timeout=600,  # 10 分钟超时
    )


def generate_daily_plan(
    llm: ChatOpenAI, trending_snapshot: str, min_slots: int = 3, max_slots: int = 5
) -> DailyPlan:
    """生成当日行动计划：穿插发帖与浏览。"""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是微博行动官，根据热点为今日生成行动日程，保证包含发帖与浏览两类动作，时间点合理分布。",
            ),
            (
                "human",
                "人设：{persona}\n热点/素材预览：{trending}\n需要 {min_slots}~{max_slots} 个时段，格式化为结构化计划。",
            ),
        ]
    )
    structured_llm = llm.with_structured_output(DailyPlan)
    return structured_llm.invoke(
        {"persona": PERSONA, "trending": trending_snapshot, "min_slots": min_slots, "max_slots": max_slots}
    )


def _summarize_trending(llm: ChatOpenAI, feed_data: Dict[str, Any]) -> str:
    """压缩 weibo_get_state 返回的关注/推荐数据，供规划使用。"""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "总结输入微博数据的热点主题，列出 3-5 个关键词和对应亮点，用于后续计划。",
            ),
            ("human", "微博数据 JSON：\n{data}"),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"data": json.dumps(feed_data, ensure_ascii=False)})


def _compose_post(llm: ChatOpenAI, topic: str, notes: Optional[str], trending: str) -> str:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "根据人设和热点写一条微博，限制 120 字内，可带 1-2 个话题标签。"),
            (
                "human",
                "人设：{persona}\n主题：{topic}\n补充：{notes}\n热点摘要：{trending}\n请输出微博正文。",
            ),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"persona": PERSONA, "topic": topic, "notes": notes or "", "trending": trending})


def _decide_browse_actions(llm: ChatOpenAI, feed_data: Dict[str, Any]) -> List[BrowseDecision]:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你要浏览微博流，对每条决定点赞/评论/转发/跳过。务必使用提供的 uid/weibo_id 填写 target_object。",
            ),
            (
                "human",
                "微博流数据 JSON：{data}\n只输出结构化决策列表，保持高质量评论/转发内容。",
            ),
        ]
    )
    structured_llm = llm.with_structured_output(BrowseDecisionList)
    result = structured_llm.invoke({"data": json.dumps(feed_data, ensure_ascii=False)})
    return result.decisions


def run_daily_workflow(
    agent_id: str,
    model: str = "gpt-4o-mini",
    min_slots: int = 3,
    max_slots: int = 5,
    n_following: int = 4,
    n_recommend: int = 4,
    tool_timeout: float = 600.0,
) -> None:
    """
    1) 拉取关注/推荐，生成热点摘要。
    2) 基于热点生成今日计划（含发帖/浏览）。
    3) 立即执行计划中的操作（发帖直接发布；浏览会逐条决定互动）。
    """
    llm = _build_llm(model=model)
    toolkit = WeiboServiceToolkit(account_list, timeout=tool_timeout)
    state_tool = WeiboGetStateTool(toolkit.base_url, toolkit.timeout)
    action_tool = WeiboActionTool(toolkit.base_url, toolkit.timeout)

    print(">>> 获取微博流用于规划...")
    raw_state = state_tool.invoke(
        {"agent_id": agent_id, "n_following": n_following, "n_recommend": n_recommend}
    )
    feed_data = json.loads(raw_state)
    trending_summary = _summarize_trending(llm, feed_data)
    print(f"热点摘要：{trending_summary}\n")

    print(">>> 生成今日计划...")
    daily_plan = generate_daily_plan(llm, trending_summary, min_slots=min_slots, max_slots=max_slots)
    print(json.dumps(daily_plan.dict(), ensure_ascii=False, indent=2))

    for item in daily_plan.items:
        print(f"\n=== 执行[{item.time}] {item.action.upper()} ===")
        if item.action == "post":
            content = _compose_post(llm, item.topic or "今日科技热点", item.notes, trending_summary)
            payload = {
                "agent_id": agent_id,
                "action_type": "post",
                "action_content": content,
                "target_object": None,
            }
            result = action_tool.invoke(payload)
            print(f"已发帖：{content}\n后台响应：{result}")
        else:
            browse_data = state_tool.invoke(
                {"agent_id": agent_id, "n_following": n_following, "n_recommend": n_recommend}
            )
            decisions = _decide_browse_actions(llm, json.loads(browse_data))
            for decision in decisions:
                if decision.action_type == "skip":
                    continue
                payload = {
                    "agent_id": agent_id,
                    "action_type": decision.action_type,
                    "action_content": decision.action_content,
                    "target_object": decision.target_object,
                }
                resp = action_tool.invoke(payload)
                print(f"已执行 {decision.action_type} -> {decision.target_object}，响应：{resp}")


if __name__ == "__main__":
    default_agent_id = str(account_list[0]["account_id"]) if account_list else ""
    run_daily_workflow(agent_id=default_agent_id)
