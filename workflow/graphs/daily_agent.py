"""
完整的Daily Agent Workflow Graph
组合schedule、post和browse的完整流程
"""
from langgraph.graph import StateGraph, END
from workflow.states.weibo_state import WeiboWorkflowState

# 导入所有需要的节点
from workflow.nodes.fetch.fetch_feed import fetch_feed_node
from workflow.nodes.analyze.summarize_trending import summarize_trending_node
from workflow.nodes.generate.generate_schedule import generate_schedule_node
from workflow.nodes.generate.compose_post import compose_post_node
from workflow.nodes.generate.review_post import review_post_node
from workflow.nodes.execute.post_weibo import post_weibo_node
from workflow.nodes.analyze.decide_interactions import decide_interactions_node
from workflow.nodes.execute.execute_interactions import execute_interactions_node

# 导入条件
from workflow.conditions.review_conditions import should_continue_review


def create_daily_agent_graph():
    """
    创建完整的daily agent workflow图
    
    流程：
    1. Schedule: 获取feed → 分析热点 → 生成计划
    2. Post: 生成草稿 → 审查(循环) → 发布
    3. Browse: 决策互动 → 执行互动
    
    Returns:
        编译后的StateGraph
    """
    workflow = StateGraph(WeiboWorkflowState)
    
    # === Schedule部分 ===
    workflow.add_node("fetch_feed", fetch_feed_node)
    workflow.add_node("summarize_trending", summarize_trending_node)
    workflow.add_node("generate_schedule", generate_schedule_node)
    
    # === Post部分 ===
    workflow.add_node("compose_post", compose_post_node)
    workflow.add_node("review_post", review_post_node)
    workflow.add_node("post_weibo", post_weibo_node)
    
    # === Browse部分 ===
    workflow.add_node("decide_interactions", decide_interactions_node)
    workflow.add_node("execute_interactions", execute_interactions_node)
    
    # === 设置流程 ===
    
    # Schedule流程
    workflow.set_entry_point("fetch_feed")
    workflow.add_edge("fetch_feed", "summarize_trending")
    workflow.add_edge("summarize_trending", "generate_schedule")
    
    # Schedule → Post
    workflow.add_edge("generate_schedule", "compose_post")
    workflow.add_edge("compose_post", "review_post")
    workflow.add_conditional_edges(
        "review_post",
        should_continue_review,
        {
            "review": "review_post",
            "post": "post_weibo",
        }
    )
    
    # Post → Browse
    workflow.add_edge("post_weibo", "decide_interactions")
    workflow.add_edge("decide_interactions", "execute_interactions")
    workflow.add_edge("execute_interactions", END)
    
    return workflow.compile()
