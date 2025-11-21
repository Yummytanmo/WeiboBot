"""
每日任务规划 Workflow
生成一天的发帖和浏览计划，返回 schedule 而不立即执行
"""
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator

if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(CURRENT_DIR)
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)
    from agent.weibo_tools import (  # noqa: E402
        WeiboGetStateTool,
        WeiboServiceToolkit,
    )
    from weibo_service.accounts import account_list  # type: ignore  # noqa: E402
    from workflow.workflow_base import BaseWorkflow, WorkflowContext  # noqa: E402
else:
    from agent.weibo_tools import WeiboGetStateTool, WeiboServiceToolkit
    from weibo_service.accounts import account_list  # type: ignore
    from workflow.workflow_base import BaseWorkflow, WorkflowContext


PERSONA = "职业：科技/AI 领域博主；风格：理性、专业、乐观；语气：简洁、有观点、有行动号召。"


class PlanItem(BaseModel):
    """单个计划项"""
    time: str = Field(..., description="今日计划的时间点，如 09:00、14:30 等格式")
    action: str = Field(..., description="post 或 browse")
    topic: Optional[str] = Field(None, description="当 action=post 时的主题或角度")
    notes: Optional[str] = Field(None, description="补充说明/素材来源/互动目标")
    priority: Optional[str] = Field("medium", description="优先级: high/medium/low")

    @validator("action")
    def _normalize_action(cls, value: str) -> str:
        value_lower = value.lower()
        if value_lower not in {"post", "browse"}:
            raise ValueError("action 必须是 post 或 browse")
        return value_lower

    @validator("priority")
    def _normalize_priority(cls, value: Optional[str]) -> str:
        if value is None:
            return "medium"
        value_lower = value.lower()
        if value_lower not in {"high", "medium", "low"}:
            return "medium"
        return value_lower


class DailySchedule(BaseModel):
    """每日计划"""
    date: str = Field(..., description="计划生成日期 YYYY-MM-DD")
    items: List[PlanItem] = Field(..., description="计划项列表")
    summary: Optional[str] = Field(None, description="今日计划总结")

    @validator("date", pre=True)
    def _default_date(cls, value: Optional[str]) -> str:
        return value or datetime.now().strftime("%Y-%m-%d")


def _build_llm(model: str = "gpt-4o-mini", temperature: float = 0.7) -> ChatOpenAI:
    """构建 LLM 实例"""
    api_key = os.getenv("YUNWU_API_KEY")
    base_url = os.getenv("YUNWU_BASE_URL")
    if not api_key or not base_url:
        raise RuntimeError("请先设置 YUNWU_API_KEY 与 YUNWU_BASE_URL 环境变量。")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
        timeout=600,
    )


def _summarize_trending(llm: ChatOpenAI, feed_data: Dict[str, Any]) -> str:
    """压缩 weibo_get_state 返回的关注/推荐数据，提取热点趋势"""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "分析输入的微博数据，总结当前热点趋势和话题，列出 3-5 个关键主题和亮点。",
            ),
            ("human", "微博数据 JSON：\n{data}"),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"data": json.dumps(feed_data, ensure_ascii=False)})


def generate_daily_schedule(
    llm: ChatOpenAI,
    trending_snapshot: str,
    min_slots: int = 4,
    max_slots: int = 8,
    min_slots: int = 3,
    max_slots: int = 5,
    start_time: str = "09:00",
    end_time: str = "22:00",
) -> DailySchedule:
    """生成当日行动计划：穿插发帖与浏览。"""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是微博行动规划专家。根据热点趋势和时间范围，生成今日的行动计划。"
                "计划要包含发帖(post)和浏览(browse)两类动作，合理分配时间。"
            ),
            (
                "human",
                "热点趋势摘要：\n{trending}\n\n"
                "时间范围：{start_time} - {end_time}\n"
                "需要生成 {min_slots} 到 {max_slots} 个行动项。\n\n"
                "请生成结构化的每日计划。",
            ),
        ]
    )
    structured_llm = llm.with_structured_output(DailySchedule)
    chain = prompt | structured_llm
    return chain.invoke({
        "trending": trending_snapshot,
        "start_time": start_time,
        "end_time": end_time,
        "min_slots": min_slots,
        "max_slots": max_slots,
    })


class DailyScheduleWorkflow(BaseWorkflow):
    """
    每日计划生成Workflow（可组合版本）
    
    从WorkflowContext中读取配置，生成每日行动计划并更新到context
    """
    
    def __init__(
        self,
        min_slots: int = 4,
        max_slots: int = 8,
        start_time: str = "09:00",
        end_time: str = "22:00",
        n_following: int = 5,
        n_recommend: int = 5,
        **kwargs: Any,
    ):
        """
        初始化每日计划workflow
        
        Args:
            min_slots: 最小计划项数量
            max_slots: 最大计划项数量
            start_time: 开始时间
            end_time: 结束时间
            n_following: 获取关注数量
            n_recommend: 获取推荐数量
        """
        super().__init__(name="DailySchedule", **kwargs)
        self.min_slots = min_slots
        self.max_slots = max_slots
        self.start_time = start_time
        self.end_time = end_time
        self.n_following = n_following
        self.n_recommend = n_recommend
    
    def _execute(self, context: WorkflowContext) -> WorkflowContext:
        """
        执行每日计划生成
        
        Args:
            context: workflow上下文
            
        Returns:
            更新后的context（包含schedule和trending_summary）
        """
        # 初始化 LLM 和工具
        print(">>> 初始化 LLM 和工具...")
        llm = _build_llm(model=context.llm_model, temperature=context.llm_temperature)
        toolkit = WeiboServiceToolkit(account_list, timeout=context.tool_timeout)
        state_tool = WeiboGetStateTool(toolkit.base_url, toolkit.timeout)
        
        # 获取微博流数据
        print(f">>> 获取微博流数据（关注 {self.n_following} 条，推荐 {self.n_recommend} 条）...")
        raw_state = state_tool.invoke(
            {
                "agent_id": context.agent_id,
                "n_following": self.n_following,
                "n_recommend": self.n_recommend,
            }
        )
        feed_data = json.loads(raw_state)
        
        # 分析热点趋势
        print(">>> 分析当前热点趋势...")
        trending_summary = _summarize_trending(llm, feed_data)
        print("\n📊 热点趋势摘要：")
        print("-" * 60)
        print(trending_summary)
        print("-" * 60)
        
        # 生成每日计划
        print(f"\n>>> 生成每日行动计划（{self.min_slots}-{self.max_slots} 个时段）...")
        daily_schedule = generate_daily_schedule(
            llm,
            trending_summary,
            min_slots=self.min_slots,
            max_slots=self.max_slots,
            start_time=self.start_time,
            end_time=self.end_time,
        )
        
        # 输出计划
        self._print_schedule(daily_schedule)
        
        # 更新context
        return context.update(
            state_data=feed_data,
            trending_summary=trending_summary,
            schedule=daily_schedule.dict(),
        )
    
    def _print_schedule(self, schedule: DailySchedule) -> None:
        """打印每日计划"""
        print("\n" + "=" * 60)
        print(f"📋 每日计划 - {schedule.date}")
        print("=" * 60)
        
        if schedule.summary:
            print(f"\n💡 计划概要：{schedule.summary}\n")
        
        print(f"共 {len(schedule.items)} 个计划项：\n")
        
        for idx, item in enumerate(schedule.items, 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                item.priority, "⚪"
            )
            action_icon = {"post": "✍️", "browse": "👀"}.get(item.action, "❓")
            
            print(f"{idx}. [{item.time}] {action_icon} {item.action.upper()} {priority_icon}")
            
            if item.topic:
                print(f"   主题: {item.topic}")
            if item.notes:
                print(f"   备注: {item.notes}")
            print()


def run_schedule_planning(
    agent_id: str,
    model: str = "gpt-4o-mini",
    min_slots: int = 4,
    max_slots: int = 8,
    start_time: str = "09:00",
    end_time: str = "22:00",
    n_following: int = 5,
    n_recommend: int = 5,
    tool_timeout: float = 600.0,
    output_file: Optional[str] = None,
) -> DailySchedule:
    """
    运行每日计划规划流程
    
    工作流程：
    1. 获取微博流数据（关注+推荐）
    2. 分析热点趋势
    3. 生成每日行动计划
    4. 输出 schedule（可选保存到文件）
    
    Args:
        agent_id: 代理账号ID
        model: 使用的LLM模型
        min_slots: 最小计划项数量
        max_slots: 最大计划项数量
        start_time: 开始时间
        end_time: 结束时间
        n_following: 获取关注数量
        n_recommend: 获取推荐数量
        tool_timeout: 工具超时时间
        output_file: 输出文件路径（可选）
    
    Returns:
        DailySchedule: 生成的每日计划
    """
    print("=" * 60)
    print("📅 每日行动计划生成器")
    print("=" * 60)
    
    # 初始化 LLM 和工具
    print("\n>>> 初始化 LLM 和工具...")
    llm = _build_llm(model=model)
    toolkit = WeiboServiceToolkit(account_list, timeout=tool_timeout)
    state_tool = WeiboGetStateTool(toolkit.base_url, toolkit.timeout)
    
    # 获取微博流数据
    print(f"\n>>> 获取微博流数据（关注 {n_following} 条，推荐 {n_recommend} 条）...")
    raw_state = state_tool.invoke(
        {"agent_id": agent_id, "n_following": n_following, "n_recommend": n_recommend}
    )
    feed_data = json.loads(raw_state)
    
    # 分析热点趋势
    print("\n>>> 分析当前热点趋势...")
    trending_summary = _summarize_trending(llm, feed_data)
    print("\n📊 热点趋势摘要：")
    print("-" * 60)
    print(trending_summary)
    print("-" * 60)
    
    # 生成每日计划
    print(f"\n>>> 生成每日行动计划（{min_slots}-{max_slots} 个时段，{start_time} 至 {end_time}）...")
    daily_schedule = generate_daily_schedule(
        llm,
        trending_summary,
        min_slots=min_slots,
        max_slots=max_slots,
        start_time=start_time,
        end_time=end_time,
    )
    
    # 输出计划
    print("\n" + "=" * 60)
    print(f"📋 每日计划 - {daily_schedule.date}")
    print("=" * 60)
    
    if daily_schedule.summary:
        print(f"\n💡 计划概要：{daily_schedule.summary}\n")
    
    print(f"共 {len(daily_schedule.items)} 个计划项：\n")
    
    for idx, item in enumerate(daily_schedule.items, 1):
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            item.priority, "⚪"
        )
        action_icon = {"post": "✍️", "browse": "👀"}.get(item.action, "❓")
        
        print(f"{idx}. [{item.time}] {action_icon} {item.action.upper()} {priority_icon}")
        
        if item.topic:
            print(f"   主题: {item.topic}")
        if item.notes:
            print(f"   备注: {item.notes}")
        print()
    
    # 保存到文件
    if output_file:
        schedule_dict = daily_schedule.dict()
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(schedule_dict, f, ensure_ascii=False, indent=2)
        print(f"✅ 计划已保存到: {output_file}")
    
    print("=" * 60)
    return daily_schedule


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="生成微博账号每日行动计划")
    parser.add_argument(
        "--agent-id",
        type=str,
        help="代理账号ID（默认使用第一个账号）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="LLM 模型名称",
    )
    parser.add_argument(
        "--min-slots",
        type=int,
        default=4,
        help="最小计划项数量",
    )
    parser.add_argument(
        "--max-slots",
        type=int,
        default=8,
        help="最大计划项数量",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        default="09:00",
        help="开始时间（HH:MM格式）",
    )
    parser.add_argument(
        "--end-time",
        type=str,
        default="22:00",
        help="结束时间（HH:MM格式）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（JSON格式）",
    )
    
    args = parser.parse_args()
    
    # 获取默认账号ID
    default_agent_id = str(account_list[0]["account_id"]) if account_list else ""
    agent_id = args.agent_id or default_agent_id
    
    if not agent_id:
        print("❌ 错误：未找到可用的代理账号")
        sys.exit(1)
    
    # 运行规划流程
    run_schedule_planning(
        agent_id=agent_id,
        model=args.model,
        min_slots=args.min_slots,
        max_slots=args.max_slots,
        start_time=args.start_time,
        end_time=args.end_time,
        output_file=args.output,
    )
