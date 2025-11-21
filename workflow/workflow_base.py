"""
Workflow基础框架
提供可组合的workflow抽象和数据传递机制
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Type, TypeVar

from langchain_core.runnables import Runnable, RunnableSequence
from pydantic import BaseModel, Field


class WorkflowContext(BaseModel):
    """
    Workflow上下文数据容器
    在多个workflow之间传递和累积数据
    """
    # 基础配置
    agent_id: str = Field(..., description="微博账号ID")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM模型名称")
    llm_temperature: float = Field(default=0.3, description="LLM温度参数")
    tool_timeout: float = Field(default=600.0, description="工具超时时间（秒）")
    
    # 微博数据
    state_data: Optional[Dict[str, Any]] = Field(None, description="微博状态数据")
    trending_summary: Optional[str] = Field(None, description="热点趋势摘要")
    
    # 计划和执行结果
    schedule: Optional[Dict[str, Any]] = Field(None, description="每日行动计划")
    posts: List[Dict[str, Any]] = Field(default_factory=list, description="生成的帖子列表")
    interactions: List[Dict[str, Any]] = Field(default_factory=list, description="互动结果列表")
    
    # 扩展数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    
    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True

    def update(self, **kwargs: Any) -> "WorkflowContext":
        """
        更新context并返回新实例（不可变更新）
        
        Args:
            **kwargs: 要更新的字段
            
        Returns:
            更新后的新WorkflowContext实例
        """
        data = self.dict()
        data.update(kwargs)
        return WorkflowContext(**data)
    
    def add_post(self, post_data: Dict[str, Any]) -> "WorkflowContext":
        """
        添加帖子到posts列表
        
        Args:
            post_data: 帖子数据
            
        Returns:
            更新后的WorkflowContext
        """
        new_posts = self.posts + [post_data]
        return self.update(posts=new_posts)
    
    def add_interaction(self, interaction_data: Dict[str, Any]) -> "WorkflowContext":
        """
        添加互动结果到interactions列表
        
        Args:
            interaction_data: 互动数据
            
        Returns:
            更新后的WorkflowContext
        """
        new_interactions = self.interactions + [interaction_data]
        return self.update(interactions=new_interactions)
    
    def set_metadata(self, key: str, value: Any) -> "WorkflowContext":
        """
        设置元数据
        
        Args:
            key: 元数据键
            value: 元数据值
            
        Returns:
            更新后的WorkflowContext
        """
        new_metadata = {**self.metadata, key: value}
        return self.update(metadata=new_metadata)


T = TypeVar("T", bound="BaseWorkflow")


class BaseWorkflow(Runnable[WorkflowContext, WorkflowContext], ABC):
    """
    Workflow基类
    所有workflow都应继承此类并实现_execute方法
    
    继承自langchain的Runnable，支持标准的invoke、batch等接口
    """
    
    def __init__(self, name: Optional[str] = None, **kwargs: Any):
        """
        初始化workflow
        
        Args:
            name: workflow名称（可选）
            **kwargs: 其他配置参数
        """
        super().__init__(**kwargs)
        self.name = name or self.__class__.__name__
        self.config: Dict[str, Any] = kwargs
    
    @abstractmethod
    def _execute(self, context: WorkflowContext) -> WorkflowContext:
        """
        执行workflow的核心逻辑（子类必须实现）
        
        Args:
            context: 输入的workflow上下文
            
        Returns:
            更新后的workflow上下文
        """
        pass
    
    def invoke(
        self,
        input: WorkflowContext,
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> WorkflowContext:
        """
        执行workflow（langchain Runnable接口）
        
        Args:
            input: 输入的WorkflowContext
            config: 运行配置（可选）
            **kwargs: 其他参数
            
        Returns:
            更新后的WorkflowContext
        """
        print(f"\n{'='*60}")
        print(f"🔧 执行 Workflow: {self.name}")
        print(f"{'='*60}")
        
        try:
            result = self._execute(input)
            print(f"✅ Workflow '{self.name}' 执行成功")
            return result
        except Exception as e:
            print(f"❌ Workflow '{self.name}' 执行失败: {e}")
            raise
    
    def __or__(self, other: "BaseWorkflow") -> "WorkflowChain":
        """
        支持使用 | 操作符串联workflow
        
        Example:
            chain = workflow1 | workflow2 | workflow3
        """
        return WorkflowChain([self, other])
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(name={self.name})"


class WorkflowChain(Runnable[WorkflowContext, WorkflowContext]):
    """
    Workflow组合链
    将多个workflow串联执行
    """
    
    def __init__(self, workflows: Sequence[BaseWorkflow]):
        """
        初始化workflow链
        
        Args:
            workflows: workflow序列
        """
        super().__init__()
        self.workflows = list(workflows)
        self.names = " → ".join(w.name for w in self.workflows)
    
    def invoke(
        self,
        input: WorkflowContext,
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> WorkflowContext:
        """
        顺序执行所有workflow
        
        Args:
            input: 输入的WorkflowContext
            config: 运行配置（可选）
            **kwargs: 其他参数
            
        Returns:
            最终的WorkflowContext
        """
        print(f"\n{'='*60}")
        print(f"🔗 执行 Workflow Chain: {self.names}")
        print(f"{'='*60}")
        
        context = input
        for workflow in self.workflows:
            context = workflow.invoke(context, config, **kwargs)
        
        print(f"\n{'='*60}")
        print(f"✅ Workflow Chain 执行完成")
        print(f"{'='*60}")
        return context
    
    def __or__(self, other: BaseWorkflow) -> "WorkflowChain":
        """
        支持继续使用 | 操作符串联workflow
        
        Example:
            chain = workflow1 | workflow2 | workflow3 | workflow4
        """
        return WorkflowChain(self.workflows + [other])
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"WorkflowChain({self.names})"


def create_chain(*workflows: BaseWorkflow) -> WorkflowChain:
    """
    创建workflow链的便捷函数
    
    Args:
        *workflows: 可变数量的workflow
        
    Returns:
        WorkflowChain实例
        
    Example:
        chain = create_chain(
            DailyScheduleWorkflow(),
            PostReviewWorkflow(),
            BrowseInteractionWorkflow(),
        )
        result = chain.invoke(context)
    """
    return WorkflowChain(workflows)


def run_chain(
    chain: WorkflowChain,
    agent_id: str,
    llm_model: str = "gpt-4o-mini",
    **kwargs: Any,
) -> WorkflowContext:
    """
    运行workflow链的便捷函数
    
    Args:
        chain: WorkflowChain实例
        agent_id: 账号ID
        llm_model: LLM模型名称
        **kwargs: 其他WorkflowContext参数
        
    Returns:
        最终的WorkflowContext
        
    Example:
        chain = create_chain(workflow1, workflow2)
        result = run_chain(chain, agent_id="123")
    """
    context = WorkflowContext(
        agent_id=agent_id,
        llm_model=llm_model,
        **kwargs,
    )
    return chain.invoke(context)
