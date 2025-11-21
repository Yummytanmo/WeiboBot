"""
Post Review Workflow Graph
使用LangGraph节点库组装帖子审查workflow
"""
from langgraph.graph import StateGraph, END
from workflow.states.weibo_state import WeiboWorkflowState
from workflow.nodes.generate.compose_post import compose_post_node
from workflow.nodes.generate.review_post import review_post_node
from workflow.nodes.execute.post_weibo import post_weibo_node
from workflow.conditions.review_conditions import should_continue_review


def create_post_review_graph():
    """
    创建帖子审查workflow图
    
    流程：生成草稿 → 审查 → (循环/发布)
    
    Returns:
        编译后的StateGraph
    """
    workflow = StateGraph(WeiboWorkflowState)
    
    # 添加节点
    workflow.add_node("compose", compose_post_node)
    workflow.add_node("review", review_post_node)
    workflow.add_node("post", post_weibo_node)
    
    # 设置入口点
    workflow.set_entry_point("compose")
    
    # 设置边
    workflow.add_edge("compose", "review")
    
    #条件边（审查循环）
    workflow.add_conditional_edges(
        "review",
        should_continue_review,
        {
            "review": "review",  # 继续审查
            "post": "post",      # 发布
        }
    )
    
    workflow.add_edge("post", END)
    
    return workflow.compile()
