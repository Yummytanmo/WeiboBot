"""
Execute Interactions节点 - 执行互动
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


def execute_interactions_node(state: WeiboWorkflowState) -> WeiboWorkflowState:
    """
    执行互动
    
    执行所有决策的互动动作
    
    Args:
        state: 当前workflow状态
        
    Returns:
        更新后的状态（interactions列表增加）
    """
    print(">>> [Execute Interactions] 执行互动...")
    
    toolkit = WeiboServiceToolkit(account_list, timeout=state["tool_timeout"])
    action_tool = WeiboActionTool(toolkit.base_url, toolkit.timeout)
    
    interactions = []
    max_actions = state.get("max_interactions", 5)
    
    for decision in state.get("interaction_decisions", [])[:max_actions]:
        if decision["action_type"] == "skip":
            continue
        
        result = action_tool.invoke({
            "agent_id": state["agent_id"],
            "action_type": decision["action_type"],
            "action_content": decision.get("action_content", ""),
            "target_object": decision["target_object"],
        })
        
        interaction_data = {
            "decision": decision,
            "result": result,
        }
        interactions.append(interaction_data)
        
        print(f"  ✓ {decision['action_type']} → {decision['target_object']}")
    
    print(f"✓ 完成 {len(interactions)} 个互动")
    
    return {
        **state,
        "interactions": interactions,
        "current_node": "execute_interactions",
    }
