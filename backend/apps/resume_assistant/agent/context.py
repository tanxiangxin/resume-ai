from dataclasses import dataclass, field

from chiren_backend.platform.llm.client import SupportsStreamingMessages
from shared.types.base_tool import ToolRegistry


@dataclass
class QueryContext:
    """Agent 运行时依赖和配置打包

    包含:
    - 运行时依赖: api_client, tool_registry
    - 模型配置: model, max_tokens, temperature
    - Agent 配置: max_iterations, stop_reasons
    - 上下文数据: system_prompt, tools_schema
    - 元数据: metadata
    """

    # 运行时依赖
    api_client: SupportsStreamingMessages  # 实际做 LLM 调用的客户端
    tool_registry: ToolRegistry  # 工具注册表

    # 模型配置
    model: str
    max_tokens: int | None = None
    temperature: float = 1.0

    # Agent 配置
    max_iterations: int = 30
    stop_reasons: set[str] = field(default_factory=lambda: {"end_turn", "stop"})

    # 元数据
    metadata: dict = field(default_factory=dict)
