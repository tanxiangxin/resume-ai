"""面向 DashScope、GitHub Models 等供应商的 OpenAI 兼容客户端。"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from chiren_backend.platform.llm.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiStreamEvent,
    ApiTextDeltaEvent,
)
from chiren_backend.platform.llm.errors import (
    AuthenticationFailure,
    ChirenApiError,
    RateLimitFailure,
    RequestFailure,
)
from chiren_backend.platform.llm.usage import UsageSnapshot
from shared.types.messages import (
    ContentBlock,
    ConversationMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

log = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 30.0


def _convert_tools_to_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将 Anthropic 工具 schema 转为 OpenAI function calling 格式。

    Anthropic 格式:
        {"name": "...", "description": "...", "input_schema": {...}}
    OpenAI 格式:
        {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
    """
    result = []
    for tool in tools:
        result.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            }
        )
    return result


def _supports_reasoning_effort(model: str) -> bool:
    """识别 OpenAI 原生 reasoning 模型，避免普通模型收到未知参数。"""
    normalized = model.casefold().strip()
    return normalized.startswith(("o1", "o3", "o4", "gpt-5"))


def _convert_messages_to_openai(
    messages: list[ConversationMessage],
    system_prompt: str | None,
) -> list[dict[str, Any]]:
    """将 Anthropic 风格消息转为 OpenAI chat 格式。

    关键差异:
    - Anthropic: system prompt 是独立参数
    - OpenAI: system prompt 是 role="system" 的消息
    - Anthropic: tool_use / tool_result 是 content block
    - OpenAI: assistant 消息携带 tool_calls，tool 结果是独立消息
    """
    openai_messages: list[dict[str, Any]] = []

    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})

    for msg in messages:
        if msg.role == "assistant":
            openai_msg = _convert_assistant_message(msg)
            openai_messages.append(openai_msg)
        elif msg.role == "user":
            # 用户消息可能包含 text 或 tool_result block
            tool_results = [b for b in msg.content if isinstance(b, ToolResultBlock)]
            text_blocks = [b for b in msg.content if isinstance(b, TextBlock)]

            if tool_results:
                # 每个工具结果都转成一条 role="tool" 的独立消息
                for tr in tool_results:
                    openai_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tr.tool_use_id,
                            "content": tr.content,
                        }
                    )
            if text_blocks:
                text = "".join(b.text for b in text_blocks)
                if text.strip():
                    openai_messages.append({"role": "user", "content": text})
            if not tool_results and not text_blocks:
                # 空用户消息理论上不该出现，这里做兜底兼容
                openai_messages.append({"role": "user", "content": ""})

    return openai_messages


def _convert_assistant_message(msg: ConversationMessage) -> dict[str, Any]:
    """将 assistant ConversationMessage 转为 OpenAI 格式。

    带 thinking 的供应商模型（例如 Kimi k2.5）会要求包含工具调用的
    assistant 消息带上 ``reasoning_content``。本地把 thinking 存成
    一等 content block，回放时再转成 OpenAI 兼容的 ``reasoning_content``。
    """
    text_parts = [b.text for b in msg.content if isinstance(b, TextBlock)]
    thinking_parts = [b.thinking for b in msg.content if isinstance(b, ThinkingBlock)]
    tool_uses = [b for b in msg.content if isinstance(b, ToolUseBlock)]

    openai_msg: dict[str, Any] = {"role": "assistant"}

    content = "".join(text_parts)
    openai_msg["content"] = content if content else None

    if tool_uses:
        openai_msg["tool_calls"] = [
            {
                "id": tu.id,
                "type": "function",
                "function": {
                    "name": tu.name,
                    "arguments": json.dumps(tu.input, ensure_ascii=False),
                },
            }
            for tu in tool_uses
        ]

    if thinking_parts:
        openai_msg["reasoning_content"] = thinking_parts[0]

    if openai_msg["content"] is None and not openai_msg.get("tool_calls"):
        openai_msg["content"] = ""

    return openai_msg


def _parse_assistant_response(response: Any) -> ConversationMessage:
    """将 OpenAI ChatCompletion 响应解析成 ConversationMessage。"""
    choice = response.choices[0]
    message = choice.message
    content: list[ContentBlock] = []

    thinking = getattr(message, "reasoning_content", None) or getattr(
        message, "reasoning", None
    )
    if thinking:
        content.append(ThinkingBlock(thinking=thinking))

    if message.content:
        content.append(TextBlock(text=message.content))

    if message.tool_calls:
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                args = {}
            content.append(
                ToolUseBlock(
                    id=tc.id,
                    name=tc.function.name,
                    input=args,
                )
            )

    return ConversationMessage(role="assistant", content=content)


class OpenAICompatibleClient:
    """OpenAI 兼容 API 客户端。

    实现与 AnthropicApiClient 相同的 SupportsStreamingMessages 协议，
    因此可以在 agent 循环里作为等价替换。
    """

    def __init__(self, api_key: str, *, base_url: str | None = None) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        self._base_url = base_url or ""
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)

    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """产出文本增量和最终消息，与 Anthropic 客户端接口保持一致。"""
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                async for event in self._stream_once(request):
                    yield event
                return
            except ChirenApiError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt >= MAX_RETRIES or not self._is_retryable(exc):
                    raise self._translate_error(exc) from exc

                delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
                log.warning(
                    "OpenAI API request failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    MAX_RETRIES + 1,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

        if last_error is not None:
            raise self._translate_error(last_error) from last_error

    async def _stream_once(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """执行单次 OpenAI chat completion 流式请求。"""
        openai_messages = _convert_messages_to_openai(
            request.messages, request.system_prompt
        )
        openai_tools = (
            _convert_tools_to_openai(request.tools) if request.tools else None
        )

        params: dict[str, Any] = {
            "model": request.model,
            "messages": openai_messages,
            "max_tokens": request.max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if openai_tools:
            params["tools"] = openai_tools
            # 部分供应商（如 Kimi）会在工具调用后续轮次中拒绝空 reasoning_content。
            # 存在工具时去掉 stream_options，避免触发要求每条 assistant 消息都带
            # reasoning_content 的模型侧 thinking 模式。
            params.pop("stream_options", None)
        if request.thinking is not None and "deepseek" in self._base_url.casefold():
            params["extra_body"] = {"thinking": {"type": request.thinking}}
        if request.thinking_effort is not None and (
            "deepseek" in self._base_url.casefold()
            or _supports_reasoning_effort(request.model)
        ):
            params["reasoning_effort"] = request.thinking_effort
        if request.temperature is not None:
            params["temperature"] = request.temperature

        # 流式输出文本增量，同时收集完整响应
        collected_content = ""
        collected_reasoning = ""
        collected_tool_calls: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None
        usage_data: dict[str, int] = {}

        stream = await self._client.chat.completions.create(**params)
        async for chunk in stream:
            if not chunk.choices:
                # 部分供应商会在末尾发送仅包含 usage 的 chunk
                if chunk.usage:
                    usage_data = {
                        "input_tokens": chunk.usage.prompt_tokens or 0,
                        "output_tokens": chunk.usage.completion_tokens or 0,
                    }
                continue

            delta = chunk.choices[0].delta
            chunk_finish = chunk.choices[0].finish_reason

            if chunk_finish:
                finish_reason = chunk_finish

            # 收集 thinking 模型的 reasoning_content，不直接展示给用户
            reasoning_piece = (
                getattr(delta, "reasoning_content", None)
                or getattr(delta, "reasoning", None)
                or ""
            )
            if reasoning_piece:
                collected_reasoning += reasoning_piece
                yield ApiTextDeltaEvent(text=reasoning_piece, is_think=True)

            # 向用户流式输出文本内容
            if delta.content:
                collected_content += delta.content
                yield ApiTextDeltaEvent(text=delta.content)

            # 收集工具调用
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in collected_tool_calls:
                        collected_tool_calls[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    entry = collected_tool_calls[idx]
                    if tc_delta.id:
                        entry["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            entry["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            entry["arguments"] += tc_delta.function.arguments

            # 如果供应商在 chunk 中返回 usage，则同步记录
            if chunk.usage:
                usage_data = {
                    "input_tokens": chunk.usage.prompt_tokens or 0,
                    "output_tokens": chunk.usage.completion_tokens or 0,
                }

        # 构建最终 ConversationMessage
        content: list[ContentBlock] = []
        if collected_reasoning:
            content.append(ThinkingBlock(thinking=collected_reasoning))
        if collected_content:
            content.append(TextBlock(text=collected_content))

        for _idx in sorted(collected_tool_calls.keys()):
            tc = collected_tool_calls[_idx]
            # 跳过部分供应商返回的空工具调用占位
            if not tc["name"]:
                continue
            try:
                args = json.loads(tc["arguments"])
            except (json.JSONDecodeError, TypeError):
                args = {}
            content.append(
                ToolUseBlock(
                    id=tc["id"],
                    name=tc["name"],
                    input=args,
                )
            )

        yield ApiMessageCompleteEvent(
            message=ConversationMessage(role="assistant", content=content),
            usage=UsageSnapshot(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
            ),
            stop_reason=finish_reason,
        )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        status = getattr(exc, "status_code", None)
        if status and status in {429, 500, 502, 503}:
            return True
        if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
            return True
        return False

    @staticmethod
    def _translate_error(exc: Exception) -> ChirenApiError:
        status = getattr(exc, "status_code", None)
        msg = str(exc)
        if status == 401 or status == 403:
            return AuthenticationFailure(msg)
        if status == 429:
            return RateLimitFailure(msg)
        return RequestFailure(msg)
