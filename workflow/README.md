# Workflow Framework 使用文档

## 概述

这是一个基于langchain的可组合workflow框架，允许将独立的workflow模块串联成复杂的工作流程。

## 核心概念

### 1. WorkflowContext

`WorkflowContext` 是在workflow之间传递数据的容器。

```python
from workflow.workflow_base import WorkflowContext

context = WorkflowContext(
    agent_id="your_agent_id",
    llm_model="gpt-4o-mini",
    llm_temperature=0.7,
    tool_timeout=600.0,
)
```

**主要字段：**
- `agent_id`: 微博账号ID（必需）
- `llm_model`: LLM模型名称
- `llm_temperature`: 温度参数
- `state_data`: 微博状态数据
- `trending_summary`: 热点趋势摘要
- `schedule`: 每日行动计划
- `posts`: 生成的帖子列表
- `interactions`: 互动结果列表
- `metadata`: 自定义元数据

### 2. BaseWorkflow

所有workflow都继承自 `BaseWorkflow`，实现langchain的 `Runnable` 协议。

```python
from workflow.workflow_base import BaseWorkflow, WorkflowContext

class MyWorkflow(BaseWorkflow):
    def _execute(self, context: WorkflowContext) -> WorkflowContext:
        # 执行workflow逻辑
        # 更新并返回context
        return context.update(metadata={"key": "value"})
```

### 3. WorkflowChain

使用 `|` 操作符或 `create_chain()` 函数组合workflow。

```python
from workflow.workflow_base import create_chain

# 方式1：使用 | 操作符
chain = workflow1 | workflow2 | workflow3

# 方式2：使用 create_chain()
chain = create_chain(workflow1, workflow2, workflow3)
```

## 可用的Workflow

### DailyScheduleWorkflow

生成每日行动计划。

```python
from workflow.daily_schedule_workflow import DailyScheduleWorkflow

schedule_wf = DailyScheduleWorkflow(
    min_slots=4,          # 最小计划项数量
    max_slots=8,          # 最大计划项数量
    start_time="09:00",   # 开始时间
    end_time="22:00",     # 结束时间
    n_following=5,        # 获取关注数量
    n_recommend=5,        # 获取推荐数量
)
```

**输出到Context:**
- `schedule`: 每日计划数据
- `trending_summary`: 热点趋势摘要
- `state_data`: 微博流数据

### PostReviewWorkflow

生成、审查并发布帖子。

```python
from workflow.post_review_workflow import PostReviewWorkflow

post_wf = PostReviewWorkflow(
    topic="AI技术进展",     # 帖子主题（可选，默认从schedule读取）
    notes="结合最新研究",    # 补充说明
    feedback_delay=5,      # 发帖后等待反馈的秒数
    max_review_rounds=2,   # 最大审查轮数
    auto_post=True,        # 是否自动发布
)
```

**输出到Context:**
- `posts`: 添加新生成的帖子

### BrowseInteractionWorkflow

浏览微博流并执行互动。

```python
from workflow.browse_interaction_workflow import BrowseInteractionWorkflow

browse_wf = BrowseInteractionWorkflow(
    n_following=5,      # 获取关注数量
    n_recommend=5,      # 获取推荐数量
    max_actions=5,      # 最大互动次数
)
```

**输出到Context:**
- `interactions`: 添加互动记录

## 使用示例

### 示例1：单独运行workflow

```python
from workflow.workflow_base import WorkflowContext
from workflow.daily_schedule_workflow import DailyScheduleWorkflow

# 创建workflow
schedule_wf = DailyScheduleWorkflow()

# 创建context
context = WorkflowContext(agent_id="123")

# 运行
result = schedule_wf.invoke(context)

# 查看结果
print(result.schedule)
```

### 示例2：组合workflow（使用 | 操作符）

```python
from workflow.workflow_base import run_chain
from workflow.daily_schedule_workflow import DailyScheduleWorkflow
from workflow.post_review_workflow import PostReviewWorkflow

# 组合workflow
chain = DailyScheduleWorkflow() | PostReviewWorkflow(auto_post=False)

# 运行
result = run_chain(chain, agent_id="123")

# 查看结果
print(f"计划: {result.schedule}")
print(f"帖子: {result.posts}")
```

### 示例3：完整流程

```python
from workflow.workflow_base import run_chain
from workflow.daily_schedule_workflow import DailyScheduleWorkflow
from workflow.post_review_workflow import PostReviewWorkflow
from workflow.browse_interaction_workflow import BrowseInteractionWorkflow

# 组合完整workflow链
chain = (
    DailyScheduleWorkflow(min_slots=3, max_slots=5)
    | PostReviewWorkflow(auto_post=True)
    | BrowseInteractionWorkflow(max_actions=3)
)

# 运行
result = run_chain(
    chain,
    agent_id="123",
    llm_model="gpt-4o-mini",
    llm_temperature=0.7,
)

# 查看完整结果
print(f"计划: {len(result.schedule['items'])} 项")
print(f"发布帖子: {len(result.posts)} 条")
print(f"互动次数: {len(result.interactions)} 次")
```

### 示例4：自定义workflow

```python
from workflow.workflow_base import BaseWorkflow, WorkflowContext

class CustomWorkflow(BaseWorkflow):
    def __init__(self, greeting: str, **kwargs):
        super().__init__(name="Custom", **kwargs)
        self.greeting = greeting
    
    def _execute(self, context: WorkflowContext) -> WorkflowContext:
        print(f"{self.greeting}, Agent {context.agent_id}!")
        return context.set_metadata("custom_key", "custom_value")

# 使用自定义workflow
custom_wf = CustomWorkflow(greeting="你好")
chain = DailyScheduleWorkflow() | custom_wf

result = run_chain(chain, agent_id="123")
```

## 运行组合示例

项目包含了详细的组合示例：

```bash
# 查看所有可用示例
python workflow/composite_workflow_example.py

# 运行特定示例
python workflow/composite_workflow_example.py --example 1

# 运行所有示例
python workflow/composite_workflow_example.py --all
```

**可用示例：**
1. 仅生成每日计划
2. 生成计划 → 发帖
3. 生成计划 → 浏览互动
4. 完整流程（计划 → 发帖 → 浏览）
5. 使用 create_chain() 函数
6. 自定义参数的workflow组合

## 独立运行模式

所有workflow仍然保留原有的独立运行函数，保持向后兼容：

```bash
# 独立运行每日计划
python workflow/daily_schedule_workflow.py --min-slots 4 --max-slots 8

# 独立运行发帖workflow
python workflow/post_review_workflow.py

# 独立运行浏览workflow
python workflow/browse_interaction_workflow.py
```

## API参考

### WorkflowContext

**方法：**
- `update(**kwargs)`: 更新字段并返回新实例
- `add_post(post_data)`: 添加帖子到posts列表
- `add_interaction(interaction_data)`: 添加互动到interactions列表
- `set_metadata(key, value)`: 设置元数据

### BaseWorkflow

**方法：**
- `invoke(context)`: 执行workflow（Runnable接口）
- `_execute(context)`: 子类需要实现的核心逻辑
- `__or__(other)`: 支持 | 操作符组合

### WorkflowChain

**方法：**
- `invoke(context)`: 顺序执行所有workflow
- `__or__(other)`: 继续添加workflow到链

### 工具函数

```python
# 创建workflow链
chain = create_chain(wf1, wf2, wf3)

# 运行workflow链
result = run_chain(
    chain,
    agent_id="123",
    llm_model="gpt-4o-mini",
    llm_temperature=0.7,
    tool_timeout=600.0,
)
```

## 最佳实践

### 1. 数据传递

使用context在workflow之间传递数据：

```python
class MyWorkflow(BaseWorkflow):
    def _execute(self, context: WorkflowContext) -> WorkflowContext:
        # 读取上游workflow的数据
        schedule = context.schedule
        
        # 处理数据
        result = self.process(schedule)
        
        # 更新context
        return context.update(processed_data=result)
```

### 2. 错误处理

在workflow中处理异常：

```python
class SafeWorkflow(BaseWorkflow):
    def _execute(self, context: WorkflowContext) -> WorkflowContext:
        try:
            # 执行可能失败的操作
            result = self.risky_operation()
            return context.set_metadata("status", "success")
        except Exception as e:
            print(f"错误: {e}")
            return context.set_metadata("status", "failed")
```

### 3. 条件执行

根据context状态决定是否执行：

```python
class ConditionalWorkflow(BaseWorkflow):
    def _execute(self, context: WorkflowContext) -> WorkflowContext:
        if not context.schedule:
            print("跳过：没有可用的计划")
            return context
        
        # 继续执行
        return self.process(context)
```

### 4. 配置复用

创建预配置的workflow组合：

```python
def create_standard_chain():
    """创建标准workflow链"""
    return (
        DailyScheduleWorkflow(min_slots=4, max_slots=6)
        | PostReviewWorkflow(auto_post=True, max_review_rounds=3)
        | BrowseInteractionWorkflow(max_actions=5)
    )

# 使用
chain = create_standard_chain()
result = run_chain(chain, agent_id="123")
```

## 故障排查

### 问题：Workflow执行失败

**检查：**
1. 环境变量是否设置（`YUNWU_API_KEY`, `YUNWU_BASE_URL`）
2. agent_id是否有效
3. 网络连接是否正常

### 问题：Context数据丢失

**解决：**
确保使用 `context.update()` 返回新实例，而不是直接修改：

```python
# ✅ 正确
return context.update(new_field="value")

# ❌ 错误
context.new_field = "value"
return context
```

### 问题：Workflow顺序错误

**解决：**
按照依赖关系排列workflow：

```python
# ✅ 正确：先生成计划，再使用计划
chain = DailyScheduleWorkflow() | PostReviewWorkflow()

# ❌ 错误：PostReviewWorkflow需要schedule数据
chain = PostReviewWorkflow() | DailyScheduleWorkflow()
```

## 高级用法

### 自定义Runnable集成

可以将任何langchain Runnable集成到workflow链中：

```python
from langchain_core.runnables import RunnableLambda

def custom_step(context: WorkflowContext) -> WorkflowContext:
    print("执行自定义步骤")
    return context.set_metadata("custom", True)

chain = (
    DailyScheduleWorkflow()
    | RunnableLambda(custom_step)
    | PostReviewWorkflow()
)
```

### 并行执行

使用langchain的并行功能：

```python
from langchain_core.runnables import RunnableParallel

# 注意：这需要确保workflow之间没有数据依赖
parallel = RunnableParallel(
    post=PostReviewWorkflow(),
    browse=BrowseInteractionWorkflow(),
)
```

## 总结

这个框架提供了：
- ✅ 可组合的workflow模块
- ✅ 基于langchain的标准接口
- ✅ 灵活的数据传递机制
- ✅ 向后兼容的独立运行模式
- ✅ 丰富的组合示例

开始使用：查看 `composite_workflow_example.py` 中的示例！
