"""
Review Post节点 - 审查帖子
"""
import sys
import os

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


class ReviewResult(BaseModel):
    """审查结果"""
    approved: bool = Field(description="是否通过审查")
    final_text: str = Field(description="最终文本（通过或改进后的）")
    suggestions: str = Field(default="", description="改进建议")


def review_post_node(state: WeiboWorkflowState) -> WeiboWorkflowState:
    """
    审查帖子
    
    检查帖子是否符合要求，如不符合则给出改进版本
    
    Args:
        state: 当前workflow状态
        
    Returns:
        更新后的状态（包含review结果）
    """
    round_num = state["review_round"] + 1
    print(f">>> [Review Post] 第 {round_num} 轮审查...")
    
    llm = build_llm(state["llm_model"], state["llm_temperature"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "审查微博文本是否：1)符合人设和主题；2)无敏感/不当内容；"
         "3)结构清晰有观点；4)字数≤120。若不符合，给出改进版本。"),
        ("human",
         "人设：{persona}\n"
         "主题：{topic}\n"
         "补充：{notes}\n"
         "待审文本：{content}\n\n请给出审查结果。"),
    ])
    
    chain = prompt | llm.with_structured_output(ReviewResult, method="function_calling")
    review = chain.invoke({
        "persona": PERSONA,
        "topic": state.get("current_post_topic", ""),
        "notes": state.get("current_post_notes", ""),
        "content": state["current_post_final"],
    })
    
    status = "✓ 通过" if review.approved else "✗ 未通过"
    print(f"{status} - 最终文本: {review.final_text}")
    if review.suggestions:
        print(f"    建议: {review.suggestions}")
    
    return {
        **state,
        "current_post_final": review.final_text,
        "review_approved": review.approved,
        "review_suggestions": review.suggestions,
        "review_round": round_num,
        "current_node": "review_post",
    }
