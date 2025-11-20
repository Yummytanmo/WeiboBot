import os
import sys
from typing import Any, Dict, List, Optional

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(CURRENT_DIR)
    if PARENT_DIR not in sys.path:
        sys.path.append(PARENT_DIR)
    from weibo_service.langchain_tools import WeiboServiceToolkit  # type: ignore
else:
    from .langchain_tools import WeiboServiceToolkit

SYSTEM_PROMPT = """你是“微博行动官”，也是一名关注 AI 科研与产业发展的科技博主。编写内容时保持专业、理性、积极向上的信息风格。任何时候都要遵循以下流程：

1. **确认账号**：先判断用户是否指定账号ID，若未指明请主动询问，或默认使用可用列表中的第一个账号。
2. **目标拆解**：在心里总结用户意图（发贴/评论/点赞/获取信息/粉丝反馈等），并分析是否需要单步或多步工具调用。
3. **工具选择策略**：
   - 发帖/评论/转发/点赞/关注/取关 → 使用 `weibo_action`，确保 `agent_id`、`action_type`、`action_content` 或 `target_object` 填写完整。
   - 获取时间线/热门内容 → 使用 `weibo_get_state`，根据需求调整 `n_following`、`n_recommend`。
   - 获取粉丝/互动反馈 → 使用 `weibo_get_feedback`，传入 `weibo_id` 时返回互动数据，不传则返回粉丝变化。
   - 回溯具体微博 → 使用 `weibo_get_record` 并提供 `uid/weibo_id`。
4. **操作规范**：
   - 所有参数以 JSON 形式传递，字段必须与工具定义一致。
   - 如果用户目标模糊或缺少必要信息（如微博链接、账号ID、评论内容），必须先向用户确认后再执行。
   - 若工具调用失败或返回 `success=False`，要分析原因并给出下一步建议。
5. **结果汇报**：把工具返回内容转换为通俗描述，并明确告知已执行的动作或获取的数据。

附加信息：
- 当前可用账号ID：{account_ids}
- 可用工具列表：
{tool_info}
"""


def _build_prompt(account_ids: str, tool_info: str) -> ChatPromptTemplate:
    system_text = SYSTEM_PROMPT.format(account_ids=account_ids, tool_info=tool_info)
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_text),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )


def create_weibo_langchain_agent(
    account_list: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    timeout: float = 600.0,
    tool_timeout: float = 600.0,
    streaming: bool = False,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
) -> AgentExecutor:
    """
    Build a LangChain AgentExecutor that talks to a custom OpenAI-compatible endpoint
    and can autonomously invoke the Weibo tools.

    Args:
        account_list: list of account configs (same格式 as weibo_service.accounts).
        api_key: OpenAI API key or第三方兼容key.
        base_url: 第三方API的HTTP入口，例如"https://api.xxx.ai/v1".
        model: 模型名称。
        temperature: LLM temperature.
        timeout: 单次 LLM 请求的超时时间（秒），默认 10 分钟。
        tool_timeout: 调用微博后台工具时的 HTTP 超时（秒），默认 10 分钟。
        streaming: 是否启用流式响应（需要 callbacks）。
        callbacks: 可选回调，常用于 StreamingStdOut 等。
    """
    toolkit = WeiboServiceToolkit(account_list, timeout=tool_timeout)
    tools = toolkit.get_tools()
    tool_info = "\n".join(f"- {tool.name}: {tool.description}" for tool in tools)

    api_key = api_key or os.getenv("YUNWU_API_KEY")
    if not api_key:
        raise ValueError("必须提供 api_key 或设置 YUNWU_API_KEY 环境变量。")

    base_url = base_url or os.getenv("YUNWU_BASE_URL")
    if not base_url:
        raise ValueError("必须提供 base_url 或设置 YUNWU_BASE_URL 环境变量。")

    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        streaming=streaming,
        callbacks=callbacks if callbacks else None,
    )

    account_ids = ", ".join(str(info["account_id"]) for info in account_list)

    prompt = _build_prompt(account_ids, tool_info)
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


def run_langchain_cli(
    account_list: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o-mini",
    streaming: bool = False,
    timeout: float = 600.0,
    tool_timeout: float = 600.0,
):
    """Quick CLI loop to chat with the LangChain agent."""
    llm_callbacks: Optional[List[BaseCallbackHandler]] = None
    if streaming:
        llm_callbacks = [StreamingStdOutCallbackHandler()]

    executor = create_weibo_langchain_agent(
        account_list,
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
        tool_timeout=tool_timeout,
        streaming=streaming,
        callbacks=llm_callbacks,
    )
    print("输入自然语言指令，代理会自主调用微博工具。输入 exit 结束。")
    chat_history: List = []
    while True:
        try:
            user_input = input("微博代理> ").strip()
        except EOFError:
            break
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        try:
            result = executor.invoke({"input": user_input, "chat_history": chat_history})
            output = result["output"]
            if streaming:
                print()
            else:
                print(output)
            chat_history.extend(
                [
                    HumanMessage(content=user_input),
                    AIMessage(content=output),
                ]
            )
        except Exception as exc:
            print(f"代理执行失败: {exc}")


if __name__ == "__main__":
    if __package__ in (None, ""):
        from weibo_service.accounts import account_list  # type: ignore
    else:
        from .accounts import account_list

    run_langchain_cli(account_list)
