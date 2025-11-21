"""
Workflow Graphs模块
导出所有可用的workflow图和辅助函数
"""
from workflow.graphs.daily_schedule import create_daily_schedule_graph
from workflow.graphs.post_review import create_post_review_graph
from workflow.graphs.browse_interaction import create_browse_interaction_graph
from workflow.graphs.daily_agent import create_daily_agent_graph
from workflow.states.weibo_state import WeiboWorkflowState


def run_graph(graph, initial_state: dict) -> dict:
    """
    运行workflow图的辅助函数
    
    Args:
        graph: 编译后的StateGraph
        initial_state: 初始状态字典
        
    Returns:
        最终状态字典
    """
    # 确保所有必需字段都有默认值
    state = {
        "agent_id": "",
        "llm_model": "gpt-4o-mini",
        "llm_temperature": 0.3,
        "tool_timeout": 600.0,
        "feed_data": None,
        "trending_summary": None,
        "schedule_items": [],
        "current_schedule_index": 0,
        "current_post_topic": None,
        "current_post_notes": None,
        "current_post_draft": None,
        "current_post_final": None,
        "review_round": 0,
        "review_approved": False,
        "review_suggestions": None,
        "max_review_rounds": 2,
        "posts": [],
        "interaction_decisions": [],
        "current_interaction_index": 0,
        "max_interactions": 5,
        "interactions": [],
        "errors": [],
        "current_node": None,
        "auto_post": True,
        "min_slots": 3,
        "max_slots": 5,
        "start_time": "09:00",
        "end_time": "22:00",
    }
    
    # 更新为用户提供的值
    state.update(initial_state)
    
    # 运行图
    final_state = graph.invoke(state)
    
    return final_state


__all__ = [
    "create_daily_schedule_graph",
    "create_post_review_graph",
    "create_browse_interaction_graph",
    "create_daily_agent_graph",
    "run_graph",
    "WeiboWorkflowState",
]
