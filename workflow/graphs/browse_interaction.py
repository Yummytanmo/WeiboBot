"""
Browse Interaction Workflow Graph
使用LangGraph节点库组装浏览互动workflow
"""
from langgraph.graph import StateGraph, END
from workflow.states.weibo_state import WeiboWorkflowState
from workflow.nodes.fetch.fetch_feed import fetch_feed_node
from workflow.nodes.analyze.decide_interactions import decide_interactions_node
from workflow.nodes.execute.execute_interactions import execute_interactions_node


def create_browse_interaction_graph():
    """
    创建浏览互动workflow图
    
    流程：获取feed → 决策互动 → 执行互动
    
    Returns:
        编译后的StateGraph
    """
    workflow = StateGraph(WeiboWorkflowState)
    
    # 添加节点
    workflow.add_node("fetch_feed", fetch_feed_node)
    workflow.add_node("decide", decide_interactions_node)
    workflow.add_node("execute", execute_interactions_node)
    
    # 设置流程
    workflow.set_entry_point("fetch_feed")
    workflow.add_edge("fetch_feed", "decide")
    workflow.add_edge("decide", "execute")
    workflow.add_edge("execute", END)
    
    return workflow.compile()
