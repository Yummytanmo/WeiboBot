"""
Daily Agent Workflow - 基于时间的智能调度器
每天开始时生成schedule，然后根据真实时间执行相应的post和browse任务
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(CURRENT_DIR)
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)
    from workflow.daily_schedule_workflow import DailyScheduleWorkflow  # noqa: E402
    from workflow.post_review_workflow import PostReviewWorkflow  # noqa: E402
    from workflow.browse_interaction_workflow import BrowseInteractionWorkflow  # noqa: E402
    from workflow.workflow_base import WorkflowContext  # noqa: E402
    from weibo_service.accounts import account_list  # type: ignore  # noqa: E402
else:
    from .daily_schedule_workflow import DailyScheduleWorkflow
    from .post_review_workflow import PostReviewWorkflow
    from .browse_interaction_workflow import BrowseInteractionWorkflow
    from .workflow_base import WorkflowContext
    from weibo_service.accounts import account_list  # type: ignore


def parse_time(time_str: str) -> Optional[datetime]:
    """
    解析时间字符串为datetime对象（只关注小时和分钟）
    
    Args:
        time_str: 时间字符串，如 "09:00", "14:30"
        
    Returns:
        datetime对象，如果解析失败返回None
    """
    try:
        # 尝试 HH:MM 格式
        return datetime.strptime(time_str, "%H:%M")
    except ValueError:
        try:
            # 尝试 H:MM 格式
            return datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return None


def should_execute_task(
    current_time: datetime,
    scheduled_time: str,
    tolerance_minutes: int = 5
) -> bool:
    """
    判断是否应该执行任务
    
    Args:
        current_time: 当前时间
        scheduled_time: 计划执行时间字符串
        tolerance_minutes: 时间容差（分钟）
        
    Returns:
        是否应该执行
    """
    scheduled_dt = parse_time(scheduled_time)
    if not scheduled_dt:
        return False
    
    # 只比较小时和分钟
    current_minutes = current_time.hour * 60 + current_time.minute
    scheduled_minutes = scheduled_dt.hour * 60 + scheduled_dt.minute
    
    # 计算时间差
    diff_minutes = current_minutes - scheduled_minutes
    
    # 在时间窗口内（scheduled_time 到 scheduled_time + tolerance）
    return 0 <= diff_minutes <= tolerance_minutes


def execute_schedule_item(
    item: Dict[str, Any],
    context: WorkflowContext,
    item_index: int
) -> WorkflowContext:
    """
    执行单个schedule项
    
    Args:
        item: schedule项数据
        context: workflow上下文
        item_index: 项索引（用于日志）
        
    Returns:
        更新后的context
    """
    action = item.get('action', '')
    time_str = item.get('time', '')
    
    print(f"\n{'='*60}")
    print(f"⏰ 执行任务 #{item_index + 1}: [{time_str}] {action.upper()}")
    print(f"{'='*60}")
    
    if action == 'post':
        topic = item.get('topic', '今日话题')
        notes = item.get('notes')
        
        print(f"📝 发帖任务: {topic}")
        
        post_workflow = PostReviewWorkflow(
            topic=topic,
            notes=notes,
            auto_post=True,
            max_review_rounds=2,
        )
        context = post_workflow.invoke(context)
        
    elif action == 'browse':
        print(f"👀 浏览任务")
        
        browse_workflow = BrowseInteractionWorkflow(
            n_following=5,
            n_recommend=5,
            max_actions=5,
        )
        context = browse_workflow.invoke(context)
    
    return context


def run_daily_workflow(
    agent_id: str,
    model: str = "gpt-4o-mini",
    min_slots: int = 3,
    max_slots: int = 5,
    check_interval: int = 60,
    tolerance_minutes: int = 5,
    run_once: bool = False,
    tool_timeout: float = 600.0,
) -> WorkflowContext:
    """
    运行基于时间的daily agent workflow
    
    工作流程：
    1. 使用DailyScheduleWorkflow生成当天的schedule
    2. 循环监控当前时间
    3. 在正确的时间点执行对应的post或browse任务
    4. 跟踪已执行任务，避免重复
    
    Args:
        agent_id: 账号ID
        model: LLM模型
        min_slots: 最小schedule项数
        max_slots: 最大schedule项数
        check_interval: 检查间隔（秒）
        tolerance_minutes: 时间容差（分钟）
        run_once: 是否只运行一次（执行当前时间点的任务后退出）
        tool_timeout: 工具超时时间
        
    Returns:
        最终的WorkflowContext
    """
    print("\n" + "="*80)
    print("🤖 Daily Agent - 智能时间调度器")
    print("="*80)
    print(f"📅 日期: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"⏰ 当前时间: {datetime.now().strftime('%H:%M:%S')}")
    print(f"🔄 检查间隔: {check_interval}秒")
    print(f"⏱️  时间容差: {tolerance_minutes}分钟")
    print("="*80)
    
    # 第一步：生成每日schedule
    print("\n>>> 第1步：生成每日行动计划...")
    schedule_workflow = DailyScheduleWorkflow(
        min_slots=min_slots,
        max_slots=max_slots,
    )
    
    context = WorkflowContext(
        agent_id=agent_id,
        llm_model=model,
        tool_timeout=tool_timeout,
    )
    
    context = schedule_workflow.invoke(context)
    
    if not context.schedule or 'items' not in context.schedule:
        print("❌ 未能生成有效的schedule")
        return context
    
    schedule_items = context.schedule['items']
    total_items = len(schedule_items)
    
    print(f"\n✅ 成功生成 {total_items} 个计划项")
    print("\n📋 今日计划概览:")
    for idx, item in enumerate(schedule_items, 1):
        action_icon = "✍️" if item.get('action') == 'post' else "👀"
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            item.get('priority', 'medium'), "⚪"
        )
        print(f"  {idx}. [{item.get('time')}] {action_icon} {item.get('action', '').upper()} {priority_icon}")
        if item.get('topic'):
            print(f"     主题: {item.get('topic')}")
    
    # 第二步：时间循环调度
    executed_items: Set[int] = set()
    
    if run_once:
        print(f"\n>>> 第2步：单次执行模式 - 执行当前时间点的任务...")
    else:
        print(f"\n>>> 第2步：持续监控模式 - 开始时间循环...")
    
    iteration = 0
    while True:
        iteration += 1
        current_time = datetime.now()
        current_time_str = current_time.strftime("%H:%M")
        
        if iteration % 10 == 1:  # 每10次迭代打印一次状态
            print(f"\n⏰ [{current_time.strftime('%H:%M:%S')}] 检查待执行任务... (已完成: {len(executed_items)}/{total_items})")
        
        # 检查每个schedule项
        for idx, item in enumerate(schedule_items):
            # 跳过已执行的任务
            if idx in executed_items:
                continue
            
            scheduled_time = item.get('time', '')
            
            # 判断是否到达执行时间
            if should_execute_task(current_time, scheduled_time, tolerance_minutes):
                try:
                    context = execute_schedule_item(item, context, idx)
                    executed_items.add(idx)
                    print(f"✅ 任务 #{idx + 1} 执行完成")
                except Exception as e:
                    print(f"❌ 任务 #{idx + 1} 执行失败: {e}")
                    # 标记为已执行，避免重复尝试
                    executed_items.add(idx)
        
        # 检查退出条件
        if run_once:
            # 单次模式：执行了至少一个任务就退出
            if len(executed_items) > 0:
                print(f"\n✅ 单次执行完成，共执行了 {len(executed_items)} 个任务")
                break
            # 如果没有任务可执行，也退出
            has_future_tasks = any(
                parse_time(item.get('time', '')) and
                parse_time(item.get('time', '')).hour * 60 + parse_time(item.get('time', '')).minute >= 
                current_time.hour * 60 + current_time.minute
                for idx, item in enumerate(schedule_items) if idx not in executed_items
            )
            if not has_future_tasks:
                print(f"\n⏭️  当前时间之后没有待执行任务，退出")
                break
        else:
            # 持续模式：所有任务完成后退出
            if len(executed_items) == total_items:
                print(f"\n🎉 所有 {total_items} 个任务已完成！")
                break
        
        # 等待下一次检查
        time.sleep(check_interval)
    
    # 打印最终统计
    print("\n" + "="*80)
    print("📊 执行统计:")
    print(f"  总任务数: {total_items}")
    print(f"  已完成: {len(executed_items)}")
    print(f"  未完成: {total_items - len(executed_items)}")
    
    if context.posts:
        print(f"  发布帖子: {len(context.posts)} 条")
    if context.interactions:
        print(f"  互动次数: {len(context.interactions)} 次")
    
    print("="*80)
    print("✅ Daily Agent 执行完成")
    print("="*80 + "\n")
    
    return context


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Daily Agent - 智能时间调度器")
    parser.add_argument(
        "--agent-id",
        type=str,
        help="账号ID（默认使用第一个账号）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="LLM模型",
    )
    parser.add_argument(
        "--min-slots",
        type=int,
        default=3,
        help="最小计划项数量",
    )
    parser.add_argument(
        "--max-slots",
        type=int,
        default=5,
        help="最大计划项数量",
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=60,
        help="检查间隔（秒）",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=5,
        help="时间容差（分钟）",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="只执行一次当前时间点的任务",
    )
    
    args = parser.parse_args()
    
    # 获取账号ID
    default_agent_id = str(account_list[0]["account_id"]) if account_list else ""
    agent_id = args.agent_id or default_agent_id
    
    if not agent_id:
        print("❌ 错误：未找到可用的账号")
        sys.exit(1)
    
    # 运行daily agent
    run_daily_workflow(
        agent_id=agent_id,
        model=args.model,
        min_slots=args.min_slots,
        max_slots=args.max_slots,
        check_interval=args.check_interval,
        tolerance_minutes=args.tolerance,
        run_once=args.run_once,
    )
