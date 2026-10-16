from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from anthropic import APIError, APIStatusError, AsyncAnthropic

from chiren_backend.platform.llm.errors import (
    AuthenticationFailure,
    ChirenApiError,
    RateLimitFailure,
    RequestFailure,
)
from chiren_backend.platform.llm.usage import UsageSnapshot
from shared.types.messages import ConversationMessage, assistant_message_from_api

log = logging.getLogger(__name__)

# 重试配置
MAX_RETRIES = 3
BASE_DELAY = 1.0  # 秒
MAX_DELAY = 30.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 529}


@dataclass(frozen=True)
class ApiMessageRequest:
    """模型调用输入参数。"""

    model: str
    messages: list[ConversationMessage]
    system_prompt: str | None = None
    max_tokens: int = 4096
    temperature: float | None = None
    thinking: Literal["enabled", "disabled"] | None = None
    thinking_effort: Literal[
        "none", "minimal", "low", "medium", "high", "max", "xhigh"
    ] | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ApiTextDeltaEvent:
    """模型输出的增量文本。"""

    text: str
    is_think: bool = False


@dataclass(frozen=True)
class ApiMessageCompleteEvent:
    """包含完整 assistant 消息的终态事件。"""

    message: ConversationMessage
    usage: UsageSnapshot
    stop_reason: str | None = None


ApiStreamEvent = ApiTextDeltaEvent | ApiMessageCompleteEvent


class SupportsStreamingMessages(Protocol):
    """测试和生产代码共用的流式消息协议。"""

    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """产出请求对应的流式事件。"""


def _is_retryable(exc: Exception) -> bool:
    """判断异常是否适合重试。"""
    if isinstance(exc, APIStatusError):
        return exc.status_code in RETRYABLE_STATUS_CODES
    if isinstance(exc, APIError):
        return True  # 网络错误可以重试
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True
    return False


def _get_retry_delay(attempt: int, exc: Exception | None = None) -> float:
    """计算带抖动的指数退避时间。"""
    import random

    # 优先使用服务端返回的 Retry-After
    if isinstance(exc, APIStatusError):
        retry_after = getattr(exc, "headers", {})
        if hasattr(retry_after, "get"):
            val = retry_after.get("retry-after")
            if val:
                try:
                    return min(float(val), MAX_DELAY)
                except (ValueError, TypeError):
                    pass

    delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
    jitter = random.uniform(0, delay * 0.25)
    return delay + jitter


class AnthropicApiClient:
    """封装 Anthropic 异步 SDK，并提供重试逻辑。"""

    def __init__(self, api_key: str, *, base_url: str | None = None) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncAnthropic(**kwargs)

    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """产出文本增量和最终消息，瞬时错误会自动重试。"""
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                async for event in self._stream_once(request):
                    yield event
                return  # 成功
            except ChirenApiError:
                raise  # 鉴权类错误不重试
            except Exception as exc:
                last_error = exc
                if attempt >= MAX_RETRIES or not _is_retryable(exc):
                    if isinstance(exc, APIError):
                        raise _translate_api_error(exc) from exc
                    raise RequestFailure(str(exc)) from exc

                delay = _get_retry_delay(attempt, exc)
                status = getattr(exc, "status_code", "?")
                log.warning(
                    "API request failed (attempt %d/%d, status=%s), retrying in %.1fs: %s",
                    attempt + 1,
                    MAX_RETRIES + 1,
                    status,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

        if last_error is not None:
            if isinstance(last_error, APIError):
                raise _translate_api_error(last_error) from last_error
            raise RequestFailure(str(last_error)) from last_error

    async def _stream_once(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """执行单次流式消息请求。"""
        params: dict[str, Any] = {
            "model": request.model,
            "messages": [message.to_api_param() for message in request.messages],
            "max_tokens": request.max_tokens,
        }
        if request.system_prompt:
            params["system"] = request.system_prompt
        if request.tools:
            params["tools"] = request.tools
        if request.thinking is not None:
            params["thinking"] = {"type": request.thinking}
        if request.thinking_effort is not None:
            params["output_config"] = {"effort": request.thinking_effort}
        if request.temperature is not None:
            params["temperature"] = request.temperature

        try:
            async with self._client.messages.stream(**params) as stream:
                async for event in stream:
                    if getattr(event, "type", None) != "content_block_delta":
                        continue
                    delta = getattr(event, "delta", None)
                    if getattr(delta, "type", None) not in (
                        "text_delta",
                        "thinking_delta",
                    ):
                        continue
                    text = getattr(delta, "text", None)
                    thinking = getattr(delta, "thinking", None)

                    if thinking:
                        yield ApiTextDeltaEvent(text=thinking, is_think=True)
                    if text:
                        yield ApiTextDeltaEvent(text=text)

                final_message = await stream.get_final_message()
        except APIError as exc:
            if (
                isinstance(exc, APIStatusError)
                and exc.status_code in RETRYABLE_STATUS_CODES
            ):
                raise  # 交给外层重试逻辑处理
            raise _translate_api_error(exc) from exc

        usage = getattr(final_message, "usage", None)
        yield ApiMessageCompleteEvent(
            message=assistant_message_from_api(final_message),
            usage=UsageSnapshot(
                input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            ),
            stop_reason=getattr(final_message, "stop_reason", None),
        )


def _translate_api_error(exc: APIError) -> ChirenApiError:
    name = exc.__class__.__name__
    if name in {"AuthenticationError", "PermissionDeniedError"}:
        return AuthenticationFailure(str(exc))
    if name == "RateLimitError":
        return RateLimitFailure(str(exc))
    return RequestFailure(str(exc))
