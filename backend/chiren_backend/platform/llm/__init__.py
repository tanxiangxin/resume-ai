"""LLM 编排辅助函数。"""

from typing import Literal

from chiren_backend.platform.llm.client import (
    AnthropicApiClient,
    SupportsStreamingMessages,
)
from chiren_backend.platform.llm.errors import ChirenApiError
from chiren_backend.platform.llm.openai_client import OpenAICompatibleClient
from chiren_backend.platform.llm.structured import call_structured_json
from chiren_backend.platform.llm.usage import UsageSnapshot

__all__ = [
    "AnthropicApiClient",
    "ChirenApiError",
    "OpenAICompatibleClient",
    "SupportsStreamingMessages",
    "UsageSnapshot",
    "call_structured_json",
    "get_client",
]


def get_client(
    provider_type: Literal["anthropic", "openai"],
    api_key: str,
    base_url: str,
) -> SupportsStreamingMessages:
    """按供应商类型创建流式 LLM 客户端。"""
    if provider_type == "openai":
        return OpenAICompatibleClient(api_key=api_key, base_url=base_url)
    if provider_type == "anthropic":
        return AnthropicApiClient(api_key=api_key, base_url=base_url)
    raise ValueError(f"不支持的 LLM 供应商类型: {provider_type}")
