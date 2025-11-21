"""
Decide Interactions节点 - 决定互动动作
"""
import sys
import os
import json
from typing import List

if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)

from workflow.states.weibo_state import WeiboWorkflowState
from workflow.utils.llm_builder import build_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field


PERSONA = "职业：科技/AI领域博主；风格：理性、专业、乐观；语气：简洁、有观点、有行动号召。"


class InteractionDecision(BaseModel):
    """单个互动决策"""
    target_object: str = Field(description="目标uid或weibo_id")
    action_type: str = Field(description="like/comment/repost/skip")
    action_content: str = Field(default="", description="评论或转发内容")
    reason: str = Field(default="", description="决策理由")


class InteractionPlan(BaseModel):
    """互动计划"""
    decisions: List[InteractionDecision]


def decide_interactions_node(state: WeiboWorkflowState) -> WeiboWorkflowState:
    """
    决定互动动作
    
    基于feed数据决定对哪些内容进行互动
    
    Args:
        state: 当前workflow状态
        
    Returns:
        更新后的状态（包含interaction_decisions）
    """
    print(">>> [Decide Interactions] 决策互动...")
    
    llm = build_llm(state["llm_model"], state["llm_temperature"])
    
    max_actions = state.get("max_interactions", 5)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "你负责浏览微博流，结合人设挑选高价值互动。"
         "最多执行{max_actions}个实际动作；不匹配的内容请skip。"
         "评论/转发要口吻自然、有观点且不超过80字。"),
        ("human",
         "人设：{persona}\n"
         "微博流数据：{data}\n\n"
         "请输出结构化决策，target_object必填uid/weibo_id。"),
    ])
    
    chain = prompt | llm.with_structured_output(InteractionPlan)
    plan = chain.invoke({
        "persona": PERSONA,
        "data": json.dumps(state["feed_data"], ensure_ascii=False),
        "max_actions": max_actions,
    })
    
    decisions =  [d.dict() for d in plan.decisions]
    print(f"✓ 生成 {len(decisions)} 个互动决策")
    
    return {
        **state,
        "interaction_decisions": decisions,
        "current_interaction_index": 0,
        "current_node": "decide_interactions",
    }
