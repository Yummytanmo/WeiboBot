"""
Post Weibo节点 - 发布微博
"""
import sys
import os

if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)

from workflow.states.weibo_state import WeiboWorkflowState
from agent.weibo_tools import WeiboActionTool, WeiboServiceToolkit
from weibo_service.accounts import account_list


def post_weibo_node(state: WeiboWorkflowState) -> WeiboWorkflowState:
    """
    发布微博
    
    将审查通过的帖子发布到微博
    
    Args:
        state: 当前workflow状态
        
    Returns:
        更新后的状态（posts列表增加一条）
    """
    print(">>> [Post Weibo] 发布微博...")
    
    toolkit = WeiboServiceToolkit(account_list, timeout=state["tool_timeout"])
    action_tool = WeiboActionTool(toolkit.base_url, toolkit.timeout)
    
    result = action_tool.invoke({
        "agent_id": state["agent_id"],
        "action_type": "post",
        "action_content": state["current_post_final"],
        "target_object": None,
    })
    
    post_data = {
        "topic": state.get("current_post_topic", ""),
        "notes": state.get("current_post_notes", ""),
        "draft": state.get("current_post_draft", ""),
        "final": state["current_post_final"],
        "review_rounds": state["review_round"],
        "posted": True,
        "result": result,
    }
    
    print(f"✓ 发布成功: {state['current_post_final']}")
    
    return {
        **state,
        "posts": [post_data],
        "current_node": "post_weibo",
    }
