"""
Review Conditions - 审查流程的条件判断
"""
from workflow.states.weibo_state import WeiboWorkflowState


def should_continue_review(state: WeiboWorkflowState) -> str:
    """
    判断是否应该继续审查
    
    Args:
        state: 当前状态
        
    Returns:
        "review" - 继续审查
        "post" - 发布帖子
    """
    # 如果通过审查，发布
    if state["review_approved"]:
        return "post"
    
    # 如果达到最大轮数，强制发布
    max_rounds = state.get("max_review_rounds", 2)
    if state["review_round"] >= max_rounds:
        return "post"
    
    # 否则继续审查
    return "review"
