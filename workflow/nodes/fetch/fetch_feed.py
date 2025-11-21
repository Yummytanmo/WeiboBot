"""
Fetch Feed节点 - 获取微博feed数据
"""
import json
import sys
import os

# 处理导入路径
if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)

from workflow.states.weibo_state import WeiboWorkflowState
from agent.weibo_tools import WeiboGetStateTool, WeiboServiceToolkit
from weibo_service.accounts import account_list


def fetch_feed_node(state: WeiboWorkflowState) -> WeiboWorkflowState:
    """
    获取微博feed数据
    
    从关注流和推荐流获取微博数据
    
    Args:
        state: 当前workflow状态
        
    Returns:
        更新后的状态（包含feed_data）
    """
    print(">>> [Fetch Feed] 获取微博feed数据...")
    
    toolkit = WeiboServiceToolkit(account_list, timeout=state["tool_timeout"])
    state_tool = WeiboGetStateTool(toolkit.base_url, toolkit.timeout)
    
    raw_state = state_tool.invoke({
        "agent_id": state["agent_id"],
        "n_following": 5,
        "n_recommend": 5,
    })
    
    feed_data = json.loads(raw_state)
    print(f"✓ 获取到 {len(feed_data.get('following', []))} 条关注流, {len(feed_data.get('recommend', []))} 条推荐流")
    
    return {
        **state,
        "feed_data": feed_data,
        "current_node": "fetch_feed",
    }
