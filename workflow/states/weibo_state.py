"""
统一的Workflow状态定义
所有基于LangGraph的workflow都使用这个状态类型
"""
from typing import TypedDict, Optional, List, Dict, Any, Annotated
from operator import add


class WeiboWorkflowState(TypedDict):
    """微博workflow的统一状态"""
    
    # === 基础配置 ===
    agent_id: str
    llm_model: str
    llm_temperature: float
    tool_timeout: float
    
    # === 数据层 ===
    feed_data: Optional[Dict[str, Any]]  # 微博feed原始数据
    trending_summary: Optional[str]       # 热点趋势摘要
    
    # === Schedule层 ===
    schedule_items: Annotated[List[Dict], add]  # 计划项列表
    current_schedule_index: int                  # 当前执行到的计划索引
    
    # === Post层 ===
    current_post_topic: Optional[str]    # 当前帖子主题
    current_post_notes: Optional[str]    # 帖子备注
    current_post_draft: Optional[str]    # 当前草稿
    current_post_final: Optional[str]    # 审查后文本
    review_round: int                     # 审查轮数
    review_approved: bool                 # 是否通过审查
    review_suggestions: Optional[str]     # 审查建议
    max_review_rounds: int                # 最大审查轮数
    posts: Annotated[List[Dict], add]    # 已发布帖子列表
    
    # === Browse层 ===
    interaction_decisions: List[Dict]     # 互动决策列表
    current_interaction_index: int        # 当前执行到的互动索引
    max_interactions: int                 # 最大互动数
    interactions: Annotated[List[Dict], add]  # 已执行互动列表
    
    # === 元数据 ===
    errors: Annotated[List[str], add]     # 错误列表
    current_node: Optional[str]           # 当前节点名称
    
    # === 配置选项 ===
    auto_post: bool                       # 是否自动发布
    min_slots: int                        # 最小计划项数量
    max_slots: int                        # 最大计划项数量
    start_time: str                       # 开始时间
    end_time: str                         # 结束时间
