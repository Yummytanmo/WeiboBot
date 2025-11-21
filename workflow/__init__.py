"""
Workflow模块 - 基于LangGraph的模块化workflow系统
"""

# 导出LangGraph workflow图
try:
    from workflow.graphs import (
        create_daily_schedule_graph,
        create_post_review_graph,
        create_browse_interaction_graph,
        create_daily_agent_graph,
        run_graph,
    )
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  LangGraph模块导入失败: {e}")
    print("请安装依赖: pip install langgraph langchain langchain-openai")
    LANGGRAPH_AVAILABLE = False
    
    # 提供占位符函数避免导入错误
    def create_daily_schedule_graph():
        raise ImportError("请安装langgraph: pip install langgraph")
    def create_post_review_graph():
        raise ImportError("请安装langgraph: pip install langgraph")
    def create_browse_interaction_graph():
        raise ImportError("请安装langgraph: pip install langgraph")
    def create_daily_agent_graph():
        raise ImportError("请安装langgraph: pip install langgraph")
    def run_graph(graph, state):
        raise ImportError("请安装langgraph: pip install langgraph")

__all__ = [
    "create_daily_schedule_graph",
    "create_post_review_graph",
    "create_browse_interaction_graph",
    "create_daily_agent_graph",
    "run_graph",
    "LANGGRAPH_AVAILABLE",
]
