import json
import os
import sys
import time
from typing import List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(CURRENT_DIR)
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)
    from agent.weibo_tools import (  # noqa: E402
        WeiboActionTool,
        WeiboFeedbackTool,
        WeiboServiceToolkit,
    )
    from weibo_service.accounts import account_list  # type: ignore  # noqa: E402
else:
    from agent.weibo_tools import WeiboActionTool, WeiboFeedbackTool, WeiboServiceToolkit
    from weibo_service.accounts import account_list  # type: ignore


PERSONA = "职业：科技/AI 领域博主；风格：理性、专业、乐观；语气：简洁、有观点、有行动号召。"


class ReviewResult(BaseModel):
    approved: bool = Field(..., description="是否允许直接发布")
    reasons: str = Field(..., description="审批结论的简要说明")
    risks: List[str] = Field(default_factory=list, description="潜在风险或敏感点")
    final_text: str = Field(..., description="审查后可直接发布的版本")


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


def _compose_post(
    llm: ChatOpenAI,
    topic: str,
    notes: Optional[str] = None,
    trending: Optional[str] = None,
) -> str:
    """按人设生成初稿。"""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "根据人设写一条微博，限制 120 字内，可带 1-2 个话题标签，但不要堆砌。"),
            (
                "human",
                "人设：{persona}\n主题：{topic}\n补充：{notes}\n热点摘要：{trending}\n请输出微博正文。",
            ),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke(
        {
            "persona": PERSONA,
            "topic": topic,
            "notes": notes or "",
            "trending": trending or "无显式热点",
        }
    )


def _review_post(
    llm: ChatOpenAI, content: str, topic: str, notes: Optional[str] = None
) -> ReviewResult:
    review_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是贴文审查智能体，需要评估文本是否：1) 符合人设与主题；"
                "2) 无敏感/不当/夸大/负面导向；3) 结构清晰，有观点与轻量行动号召；"
                "4) 字数 <= 120。若存在问题，给出改进版本。",
            ),
            (
                "human",
                "人设：{persona}\n主题：{topic}\n补充：{notes}\n待审文本：{content}\n"
                "请给出审查结果并提供满足要求的 final_text。",
            ),
        ]
    )
    structured_llm = llm.with_structured_output(ReviewResult, method="function_calling")
    chain = review_prompt | structured_llm
    return chain.invoke(
        {
            "persona": PERSONA,
            "topic": topic,
            "notes": notes or "",
            "content": content,
        }
    )


def run_post_review_workflow(
    agent_id: str,
    topic: str,
    notes: Optional[str] = None,
    trending: Optional[str] = None,
    model: str = "gpt-4o-mini",
    tool_timeout: float = 600.0,
    feedback_delay: int = 5,
    max_review_rounds: int = 2,
) -> dict:
    """
    1) 生成初稿。
    2) 贴文审查智能体审核并修正，最多 max_review_rounds 轮。
    3) 发帖并拉取互动反馈（如可用）。
    """
    llm = _build_llm(model=model)
    toolkit = WeiboServiceToolkit(account_list, timeout=tool_timeout)
    action_tool = WeiboActionTool(toolkit.base_url, toolkit.timeout)
    feedback_tool = WeiboFeedbackTool(toolkit.base_url, toolkit.timeout)

    print(">>> 生成初稿...")
    draft = _compose_post(llm, topic, notes, trending)
    print(draft)

    latest_text = draft
    review_result: Optional[ReviewResult] = None
    for round_idx in range(max_review_rounds):
        print(f"\n>>> 审查第 {round_idx + 1} 轮...")
        review_result = _review_post(llm, latest_text, topic, notes)
        print(json.dumps(review_result.dict(), ensure_ascii=False, indent=2))
        latest_text = review_result.final_text or latest_text
        if review_result.approved:
            break

    print("\n>>> 发帖...")
    action_payload = {
        "agent_id": agent_id,
        "action_type": "post",
        "action_content": latest_text,
        "target_object": None,
    }
    action_resp_raw = action_tool.invoke(action_payload)
    print(f"后台响应：{action_resp_raw}")

    weibo_id: Optional[str] = None
    try:
        parsed = json.loads(action_resp_raw)
        data = parsed.get("data")
        if data:
            weibo_id = str(data)
    except json.JSONDecodeError:
        pass

    feedback_data: Optional[dict] = None
    if weibo_id:
        if feedback_delay > 0:
            time.sleep(feedback_delay)
        try:
            feedback_raw = feedback_tool.invoke({"agent_id": agent_id, "weibo_id": weibo_id})
            feedback_data = json.loads(feedback_raw)
            print(f"互动反馈：{json.dumps(feedback_data, ensure_ascii=False, indent=2)}")
        except Exception as exc:  # noqa: BLE001
            print(f"获取反馈失败：{exc}")

    return {
        "draft": draft,
        "final": latest_text,
        "review": review_result.dict() if review_result else {},
        "posted_weibo_id": weibo_id,
        "feedback": feedback_data,
    }


if __name__ == "__main__":
    default_agent_id = str(account_list[0]["account_id"]) if account_list else ""
    run_post_review_workflow(agent_id=default_agent_id, topic="今日 AI 热点")
