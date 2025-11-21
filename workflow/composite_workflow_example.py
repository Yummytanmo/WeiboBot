"""
组合Workflow示例
展示如何使用workflow框架组合多个workflow
"""
import os
import sys

# 添加父目录到路径
if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(CURRENT_DIR)
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)

from workflow.workflow_base import WorkflowContext, create_chain, run_chain  # noqa: E402
from workflow.daily_schedule_workflow import DailyScheduleWorkflow  # noqa: E402
from workflow.post_review_workflow import PostReviewWorkflow  # noqa: E402
from workflow.browse_interaction_workflow import BrowseInteractionWorkflow  # noqa: E402
from weibo_service.accounts import account_list  # noqa: E402


def example1_schedule_only():
    """
    示例1：仅生成每日计划
    """
    print("\n" + "="*80)
    print("示例1：仅生成每日计划")
    print("="*80)
    
    # 获取账号ID
    agent_id = str(account_list[0]["account_id"]) if account_list else ""
    
    # 创建workflow
    schedule_workflow = DailyScheduleWorkflow(
        min_slots=3,
        max_slots=5,
        start_time="09:00",
        end_time="21:00",
    )
    
    # 创建context并运行
    context = WorkflowContext(agent_id=agent_id)
    result = schedule_workflow.invoke(context)
    
    print("\n📋 生成的计划：")
    print(result.schedule)


def example2_schedule_then_post():
    """
    示例2：生成计划 → 发帖
    使用 | 操作符串联workflow
    """
    print("\n" + "="*80)
    print("示例2：生成计划 → 发帖")
    print("="*80)
    
    agent_id = str(account_list[0]["account_id"]) if account_list else ""
    
    # 使用 | 操作符组合workflow
    chain = (
        DailyScheduleWorkflow(min_slots=2, max_slots=4)
        | PostReviewWorkflow(auto_post=False)  # 仅生成不发布
    )
    
    # 运行链
    result = run_chain(chain, agent_id=agent_id)
    
    print("\n📊 执行结果：")
    print(f"- 计划项数量: {len(result.schedule.get('items', []))}")
    print(f"- 生成帖子数量: {len(result.posts)}")
    for idx, post in enumerate(result.posts, 1):
        print(f"\n帖子 {idx}:")
        print(f"  主题: {post['topic']}")
        print(f"  内容: {post['final']}")


def example3_schedule_then_browse():
    """
    示例3：生成计划 → 浏览互动
    """
    print("\n" + "="*80)
    print("示例3：生成计划 → 浏览互动")
    print("="*80)
    
    agent_id = str(account_list[0]["account_id"]) if account_list else ""
    
    # 组合workflow
    chain = (
        DailyScheduleWorkflow()
        | BrowseInteractionWorkflow(max_actions=3)
    )
    
    result = run_chain(chain, agent_id=agent_id)
    
    print("\n📊 执行结果：")
    print(f"- 计划项数量: {len(result.schedule.get('items', []))}")
    print(f"- 互动次数: {len(result.interactions)}")


def example4_full_chain():
    """
    示例4：完整流程
    生成计划 → 发帖 → 浏览互动
    """
    print("\n" + "="*80)
    print("示例4：完整流程 (计划 → 发帖 → 浏览)")
    print("="*80)
    
    agent_id = str(account_list[0]["account_id"]) if account_list else ""
    
    # 组合完整workflow链
    chain = (
        DailyScheduleWorkflow(min_slots=3, max_slots=5)
        | PostReviewWorkflow(auto_post=True)
        | BrowseInteractionWorkflow(max_actions=5)
    )
    
    result = run_chain(
        chain,
        agent_id=agent_id,
        llm_model="gpt-4o-mini",
    )
    
    print("\n📊 最终执行结果：")
    print(f"- 生成计划: {result.schedule.get('date')}")
    print(f"- 计划项数量: {len(result.schedule.get('items', []))}")
    print(f"- 发布帖子数量: {len(result.posts)}")
    print(f"- 互动次数: {len(result.interactions)}")
    
    # 显示详细信息
    print("\n📝 发布的帖子:")
    for idx, post in enumerate(result.posts, 1):
        status = "✅ 已发布" if post.get("posted") else "📝 仅生成"
        print(f"{idx}. {status} - {post['topic']}")
        print(f"   {post['final'][:60]}...")
    
    print("\n💬 互动记录:")
    for idx, interaction in enumerate(result.interactions, 1):
        decision = interaction.get("decision", {})
        action_type = decision.get("action_type", "unknown")
        target = decision.get("target_object", "unknown")
        print(f"{idx}. {action_type} → {target}")


def example5_create_chain_function():
    """
    示例5：使用 create_chain() 函数
    """
    print("\n" + "="*80)
    print("示例5：使用 create_chain() 函数")
    print("="*80)
    
    agent_id = str(account_list[0]["account_id"]) if account_list else ""
    
    # 使用 create_chain 函数
    chain = create_chain(
        DailyScheduleWorkflow(min_slots=2, max_slots=3),
        PostReviewWorkflow(auto_post=False),
        BrowseInteractionWorkflow(max_actions=2),
    )
    
    result = run_chain(chain, agent_id=agent_id)
    
    print("\n📊 执行结果汇总:")
    print(f"- Schedule: ✅")
    print(f"- Posts: {len(result.posts)}")
    print(f"- Interactions: {len(result.interactions)}")


def example6_custom_workflow():
    """
    示例6：自定义参数的workflow组合
    """
    print("\n" + "="*80)
    print("示例6：自定义参数的workflow组合")
    print("="*80)
    
    agent_id = str(account_list[0]["account_id"]) if account_list else ""
    
    # 创建高度自定义的workflow
    custom_schedule = DailyScheduleWorkflow(
        min_slots=5,
        max_slots=8,
        start_time="08:00",
        end_time="23:00",
        n_following=10,
        n_recommend=10,
    )
    
    custom_post = PostReviewWorkflow(
        topic="AI代理技术最新进展",
        notes="结合最新论文和实践经验",
        max_review_rounds=3,
        auto_post=False,
    )
    
    custom_browse = BrowseInteractionWorkflow(
        n_following=8,
        n_recommend=8,
        max_actions=10,
    )
    
    # 组合
    chain = custom_schedule | custom_post | custom_browse
    
    # 运行并指定高级参数
    result = run_chain(
        chain,
        agent_id=agent_id,
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        tool_timeout=900.0,
    )
    
    print(f"\n✅ 完成！共执行了 {len(result.posts)} 个发帖任务和 {len(result.interactions)} 次互动")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Workflow组合示例")
    parser.add_argument(
        "--example",
        type=int,
        choices=[1, 2, 3, 4, 5, 6],
        help="运行指定示例（1-6）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="运行所有示例",
    )
    
    args = parser.parse_args()
    
    examples = {
        1: example1_schedule_only,
        2: example2_schedule_then_post,
        3: example3_schedule_then_browse,
        4: example4_full_chain,
        5: example5_create_chain_function,
        6: example6_custom_workflow,
    }
    
    if args.all:
        print("\n🚀 运行所有示例...\n")
        for num, func in examples.items():
            func()
            print("\n" + "-"*80 + "\n")
    elif args.example:
        examples[args.example]()
    else:
        print("请使用 --example N 运行指定示例，或 --all 运行所有示例")
        print("\n可用示例：")
        print("  1. 仅生成每日计划")
        print("  2. 生成计划 → 发帖")
        print("  3. 生成计划 → 浏览互动")
        print("  4. 完整流程（计划 → 发帖 → 浏览）")
        print("  5. 使用 create_chain() 函数")
        print("  6. 自定义参数的workflow组合")
