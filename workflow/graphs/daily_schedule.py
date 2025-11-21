"""
Daily Schedule Workflow Graph
使用LangGraph节点库组装每日计划workflow
"""
from langgraph.graph import StateGraph, END
from workflow.states.weibo_state import WeiboWorkflowState
from workflow.nodes.fetch.fetch_feed import fetch_feed_node
from workflow.nodes.analyze.summarize_trending import summarize_trending_node
from workflow.nodes.generate.generate_schedule import generate_schedule_node


def create_daily_schedule_graph():
    """
    创建每日计划workflow图
    
    流程：获取feed → 分析热点 → 生成计划
    
    Returns:
        编译后的StateGraph
    """
    workflow = StateGraph(WeiboWorkflowState)
    
    # 添加节点（从节点库导入）
    workflow.add_node("fetch_feed", fetch_feed_node)
    workflow.add_node("summarize_trending", summarize_trending_node)
    workflow.add_node("generate_schedule", generate_schedule_node)
    
    # 设置入口点和流程
    workflow.set_entry_point("fetch_feed")
    workflow.add_edge("fetch_feed", "summarize_trending")
    workflow.add_edge("summarize_trending", "generate_schedule")
    workflow.add_edge("generate_schedule", END)
    
    return workflow.compile()
