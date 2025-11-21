"""
Generate Schedule节点 - 生成每日计划
"""
import sys
import os
from datetime import datetime
from typing import List

if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)

from workflow.states.weibo_state import WeiboWorkflowState
from workflow.utils.llm_builder import build_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field


class ScheduleItem(BaseModel):
    """计划项"""
    time: str = Field(description="时间，如09:00")
    action: str = Field(description="post或browse")
    topic: str = Field(default="", description="帖子主题（仅post时需要）")
    priority: str = Field(default="medium", description="优先级：high/medium/low")


class DailySchedule(BaseModel):
    """每日计划"""
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    items: List[ScheduleItem]
    summary: str = Field(default="", description="计划概要")


def generate_schedule_node(state: WeiboWorkflowState) -> WeiboWorkflowState:
    """
    生成每日计划
    
    基于热点趋势生成当天的行动计划
    
    Args:
        state: 当前workflow状态
        
    Returns:
        更新后的状态（包含schedule_items）
    """
    print(">>> [Generate Schedule] 生成每日计划...")
    
    llm = build_llm(state["llm_model"], state["llm_temperature"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "生成今日微博行动计划。计划要包含发帖(post)和浏览(browse)两类行动，合理分配时间。"),
        ("human",
         "热点趋势：\n{trending}\n\n"
         "时间范围：{start_time} - {end_time}\n"
         "生成 {min_slots} 到 {max_slots} 个行动项。"),
    ])
    
    chain = prompt | llm.with_structured_output(DailySchedule)
    schedule = chain.invoke({
        "trending": state["trending_summary"],
        "start_time": state.get("start_time", "09:00"),
        "end_time": state.get("end_time", "22:00"),
        "min_slots": state.get("min_slots", 3),
        "max_slots": state.get("max_slots", 5),
    })
    
    items = [item.dict() for item in schedule.items]
    
    print(f"✓ 生成 {len(items)} 个计划项")
    for idx, item in enumerate(items, 1):
        action_icon = "✍️" if item["action"] == "post" else "👀"
        print(f"  {idx}. [{item['time']}] {action_icon} {item['action'].upper()}")
        if item.get("topic"):
            print(f"     主题: {item['topic']}")
    
    return {
        **state,
        "schedule_items": items,
        "current_schedule_index": 0,
        "current_node": "generate_schedule",
    }
