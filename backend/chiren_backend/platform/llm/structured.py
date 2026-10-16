"""基于流式模型客户端的结构化 JSON 调用。"""

import json
import logging
from collections.abc import Callable
from typing import Literal

import json_repair
from pydantic import BaseModel, ValidationError

from chiren_backend.platform.llm.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiTextDeltaEvent,
    SupportsStreamingMessages,
)
from shared.types.messages import ConversationMessage, TextBlock

log = logging.getLogger(__name__)
MAX_STRUCTURED_OUTPUT_TOKENS = 32768


async def call_structured_json[T: BaseModel](
    client: SupportsStreamingMessages,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema_class: type[T],
    *,
    max_retries: int = 3,
    max_tokens: int = 4096,
    temperature: float | None = 0.0,
    thinking: Literal["enabled", "disabled"] | None = "enabled",
    thinking_effort: Literal[
        "none", "minimal", "low", "medium", "high", "max", "xhigh"
    ] | None = "medium",
    post_validator: Callable[[T], str | None] | None = None,
    invalid_response_prefix: str = "Validation failed",
) -> T:
    """调用 LLM，并用 Pydantic 模型校验 JSON 响应。

    Args:
        client: 流式 LLM 客户端。
        model: 供应商模型名称。
        system_prompt: 请求使用的 system prompt。
        user_prompt: 初始用户 prompt。
        schema_class: 期望 JSON 响应匹配的 Pydantic 模型。
        max_retries: 最大校验尝试次数。
        max_tokens: 请求最大 token 数。
        temperature: 可选采样温度。
        post_validator: 可选领域后校验，返回错误提示。
        invalid_response_prefix: 模型纠错提示前缀。

    Returns:
        解析并校验后的模型实例。
    """
    messages = [ConversationMessage.from_user_text(user_prompt)]
    current_max_tokens = max_tokens

    for attempt in range(max_retries):
        raw_content, complete_event = await _stream_text(
            client,
            ApiMessageRequest(
                model=model,
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=current_max_tokens,
                temperature=temperature,
                thinking=thinking,
                thinking_effort=thinking_effort,
            ),
        )

        if not raw_content.strip():
            reason = (
                "empty response after output token limit"
                if complete_event.stop_reason in {"length", "max_tokens"}
                else "empty response"
            )
            _log_attempt_failure(
                schema_class,
                attempt,
                max_retries,
                reason,
                complete_event.stop_reason,
                current_max_tokens,
            )
            if attempt == max_retries - 1:
                raise ValueError(
                    "LLM returned no visible structured content "
                    f"(stop_reason={complete_event.stop_reason!r})"
                )
            _append_retry_messages(
                messages,
                complete_event,
                f"{invalid_response_prefix}: empty response. "
                + (
                    "The previous response was truncated by the output token limit. "
                    "Return a more concise complete JSON object."
                    if complete_event.stop_reason in {"length", "max_tokens"}
                    else "Return the complete JSON object now; do not return an empty response."
                ),
            )
            current_max_tokens = _increase_output_budget(
                current_max_tokens, complete_event.stop_reason
            )
            continue

        try:
            parsed = json_repair.loads(raw_content)
            if not isinstance(parsed, dict):
                raise TypeError(f"expected a JSON object, got {type(parsed).__name__}")
            result = schema_class.model_validate(parsed)
        except ValidationError as exc:
            retry_message = _format_validation_error(exc, invalid_response_prefix)
            _log_attempt_failure(
                schema_class,
                attempt,
                max_retries,
                "schema validation: " + retry_message,
                complete_event.stop_reason,
                current_max_tokens,
            )
            if attempt == max_retries - 1:
                raise
            _append_retry_messages(
                messages,
                complete_event,
                retry_message,
            )
            current_max_tokens = _increase_output_budget(
                current_max_tokens, complete_event.stop_reason
            )
            continue
        except TypeError as exc:
            retry_message = (
                f"{invalid_response_prefix}: {exc}. "
                "Return one JSON object matching the requested schema."
            )
            _log_attempt_failure(
                schema_class,
                attempt,
                max_retries,
                "type validation: " + str(exc),
                complete_event.stop_reason,
                current_max_tokens,
            )
            if attempt == max_retries - 1:
                raise ValueError(f"{invalid_response_prefix}: {exc}") from exc
            _append_retry_messages(
                messages,
                complete_event,
                retry_message,
            )
            current_max_tokens = _increase_output_budget(
                current_max_tokens, complete_event.stop_reason
            )
            continue
        except json.JSONDecodeError:
            _log_attempt_failure(
                schema_class,
                attempt,
                max_retries,
                "invalid JSON",
                complete_event.stop_reason,
                current_max_tokens,
            )
            if attempt == max_retries - 1:
                raise
            retry_hint = (
                " The previous output was truncated; return a shorter complete object."
                if complete_event.stop_reason in {"length", "max_tokens"}
                else ""
            )
            _append_retry_messages(
                messages,
                complete_event,
                f"{invalid_response_prefix}: invalid JSON. "
                f"Please retry with valid JSON only.{retry_hint}",
            )
            current_max_tokens = _increase_output_budget(
                current_max_tokens, complete_event.stop_reason
            )
            continue

        if post_validator is not None:
            error = post_validator(result)
            if error:
                _log_attempt_failure(
                    schema_class,
                    attempt,
                    max_retries,
                    "post-validation: " + error,
                    complete_event.stop_reason,
                    current_max_tokens,
                )
                if attempt == max_retries - 1:
                    raise ValueError(error)
                _append_retry_messages(messages, complete_event, error)
                current_max_tokens = _increase_output_budget(
                    current_max_tokens, complete_event.stop_reason
                )
                continue

        return result

    raise RuntimeError("Max retries exceeded")


def _log_attempt_failure(
    schema_class: type[BaseModel],
    attempt: int,
    max_retries: int,
    reason: str,
    stop_reason: str | None,
    max_tokens: int,
) -> None:
    """记录结构化输出每次失败的原因，但不记录模型原文。"""
    log.warning(
        "structured_json.retry schema=%s attempt=%d/%d max_tokens=%d "
        "stop_reason=%s reason=%s",
        schema_class.__name__,
        attempt + 1,
        max_retries,
        max_tokens,
        stop_reason or "unknown",
        reason[:500],
    )


def _increase_output_budget(max_tokens: int, stop_reason: str | None) -> int:
    """仅在输出被截断时扩大预算，并限制在供应商兼容上限内。"""
    if stop_reason not in {"length", "max_tokens"}:
        return max_tokens
    return min(max_tokens * 2, MAX_STRUCTURED_OUTPUT_TOKENS)


async def _stream_text(
    client: SupportsStreamingMessages,
    request: ApiMessageRequest,
) -> tuple[str, ApiMessageCompleteEvent]:
    """收集可见文本增量和最终 assistant 消息。"""
    raw_content = ""
    complete_event: ApiMessageCompleteEvent | None = None

    async for event in client.stream_message(request):
        if isinstance(event, ApiTextDeltaEvent):
            if event.is_think:
                continue
            raw_content += event.text
        elif isinstance(event, ApiMessageCompleteEvent):
            complete_event = event

    if complete_event is None:
        raise RuntimeError("LLM did not return a completion event")

    if not raw_content.strip():
        raw_content = "".join(
            block.text
            for block in complete_event.message.content
            if isinstance(block, TextBlock)
        )

    return raw_content, complete_event


def _append_retry_messages(
    messages: list[ConversationMessage],
    complete_event: ApiMessageCompleteEvent,
    correction_prompt: str,
) -> None:
    """追加 assistant 输出和纠错提示，用于下一轮尝试。"""
    messages.append(complete_event.message)
    messages.append(ConversationMessage.from_user_text(correction_prompt))


def _format_validation_error(exc: ValidationError, prefix: str) -> str:
    """格式化 Pydantic 校验错误，供模型自我修正。"""
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err["loc"])
        errors.append(f"  - {field}: {err['msg']}")
    return f"{prefix}:\n" + "\n".join(errors)
