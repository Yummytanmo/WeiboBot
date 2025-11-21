"""
LLM构建工具
"""
import os
from langchain_openai import ChatOpenAI


def build_llm(model: str = "gpt-4o-mini", temperature: float = 0.3) -> ChatOpenAI:
    """
    构建LLM实例
    
    Args:
        model: 模型名称
        temperature: 温度参数
        
    Returns:
        ChatOpenAI实例
    """
    api_key = os.getenv("YUNWU_API_KEY")
    base_url = os.getenv("YUNWU_BASE_URL")
    
    if not api_key or not base_url:
        raise RuntimeError("请设置 YUNWU_API_KEY 和 YUNWU_BASE_URL 环境变量")
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
        timeout=600,
    )
