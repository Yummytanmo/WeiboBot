"""
Summarize Trending节点 - 分析热点趋势
"""
import json
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


def summarize_trending_node(state: WeiboWorkflowState) -> WeiboWorkflowState:
    """
    分析热点趋势
    
    从feed数据中提取热点主题和趋势
    
    Args:
        state: 当前workflow状态
        
    Returns:
        更新后的状态（包含trending_summary）
    """
    print(">>> [Summarize Trending] 分析热点趋势...")
    
    llm = build_llm(state["llm_model"], state["llm_temperature"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "总结微博数据的热点主题，列出3-5个关键词和对应亮点，用于后续规划。"),
        ("human", "微博数据：\n{data}"),
    ])
    
    chain = prompt | llm | StrOutputParser()
    summary = chain.invoke({
        "data": json.dumps(state["feed_data"], ensure_ascii=False)
    })
    
    print(f"✓ 热点摘要：\n{summary}")
    
    return {
        **state,
        "trending_summary": summary,
        "current_node": "summarize_trending",
    }
