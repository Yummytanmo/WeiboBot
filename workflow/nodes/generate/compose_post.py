"""
Compose Post节点 - 生成帖子草稿
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
from langchain_core.output_parsers import StrOutputParser


PERSONA = "职业：科技/AI领域博主；风格：理性、专业、乐观；语气：简洁、有观点、有行动号召。"


def compose_post_node(state: WeiboWorkflowState) -> WeiboWorkflowState:
    """
    生成帖子草稿
    
    根据主题和热点生成微博文本
    
    Args:
        state: 当前workflow状态
        
    Returns:
        更新后的状态（包含current_post_draft和current_post_final）
    """
    topic = state.get("current_post_topic", "今日话题")
    notes = state.get("current_post_notes")
    
    print(f">>> [Compose Post] 生成帖子草稿...")
    print(f"    主题: {topic}")
    
    llm = build_llm(state["llm_model"], state["llm_temperature"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "根据人设和热点生成微博帖子，限120字内，可带1-2个话题标签。"),
        ("human",
         "人设：{persona}\n"
         "主题：{topic}\n"
         "补充：{notes}\n"
         "热点：{trending}\n\n请生成微博正文。"),
    ])
    
    chain = prompt | llm | StrOutputParser()
    draft = chain.invoke({
        "persona": PERSONA,
        "topic": topic,
        "notes": notes or "",
        "trending": state.get("trending_summary", ""),
    })
    
    print(f"✓ 草稿: {draft}")
    
    return {
        **state,
        "current_post_draft": draft,
        "current_post_final": draft,
        "review_round": 0,
        "review_approved": False,
        "current_node": "compose_post",
    }
