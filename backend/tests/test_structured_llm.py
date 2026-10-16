"""结构化 LLM 调用辅助函数测试。"""

import asyncio
from collections.abc import AsyncIterator

from pydantic import BaseModel

from chiren_backend.platform.llm import call_structured_json
from chiren_backend.platform.llm.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiStreamEvent,
    ApiTextDeltaEvent,
)
from chiren_backend.platform.llm.usage import UsageSnapshot
from shared.types.messages import ConversationMessage


class ExampleResult(BaseModel):
    """测试用结构化响应。"""

    name: str
    score: int


class FakeStreamingClient:
    """按预设响应返回流式事件的测试客户端。"""

    def __init__(self, responses: list[list[ApiStreamEvent]]) -> None:
        self.responses = responses
        self.requests: list[ApiMessageRequest] = []

    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        self.requests.append(request)
        response = self.responses[len(self.requests) - 1]
        for event in response:
            yield event


def _complete_message(
    text: str, stop_reason: str | None = None
) -> ApiMessageCompleteEvent:
    """构建测试用完成事件。"""
    return ApiMessageCompleteEvent(
        message=ConversationMessage.from_user_text(text).model_copy(
            update={"role": "assistant"}
        ),
        usage=UsageSnapshot(input_tokens=1, output_tokens=1),
        stop_reason=stop_reason,
    )


def test_call_structured_json_ignores_thinking_and_parses_text() -> None:
    """确保 thinking 增量不会进入 JSON 解析内容。"""

    async def run_case() -> None:
        client = FakeStreamingClient(
            [
                [
                    ApiTextDeltaEvent(text="内部思考", is_think=True),
                    ApiTextDeltaEvent(text='{"name":"ok","score":100}'),
                    _complete_message('{"name":"ok","score":100}'),
                ]
            ]
        )

        result = await call_structured_json(
            client,
            "model",
            "system",
            "user",
            ExampleResult,
        )

        assert result == ExampleResult(name="ok", score=100)
        assert client.requests[0].temperature == 0.0
        assert client.requests[0].thinking == "enabled"
        assert client.requests[0].thinking_effort == "medium"

    asyncio.run(run_case())


def test_call_structured_json_retries_after_validation_error(caplog) -> None:
    """确保校验失败后会把错误反馈给模型并重试。"""

    async def run_case() -> None:
        client = FakeStreamingClient(
            [
                [
                    ApiTextDeltaEvent(text='{"name":"bad","score":"oops"}'),
                    _complete_message('{"name":"bad","score":"oops"}'),
                ],
                [
                    ApiTextDeltaEvent(text='{"name":"fixed","score":88}'),
                    _complete_message('{"name":"fixed","score":88}'),
                ],
            ]
        )

        result = await call_structured_json(
            client,
            "model",
            "system",
            "user",
            ExampleResult,
            max_retries=2,
        )

        assert result == ExampleResult(name="fixed", score=88)
        assert len(client.requests) == 2
        assert "Validation failed" in client.requests[1].messages[-1].text
        assert "structured_json.retry" in caplog.text
        assert "schema=ExampleResult" in caplog.text

    asyncio.run(run_case())


def test_call_structured_json_recovers_text_from_complete_event() -> None:
    """完成事件带文本时，即使没有文本增量也应能解析。"""

    async def run_case() -> None:
        client = FakeStreamingClient(
            [[_complete_message('{"name":"recovered","score":77}')]]
        )

        result = await call_structured_json(
            client,
            "model",
            "system",
            "user",
            ExampleResult,
        )

        assert result == ExampleResult(name="recovered", score=77)

    asyncio.run(run_case())


def test_call_structured_json_retries_after_empty_response() -> None:
    """空响应应反馈为可重试错误，而不是交给 Pydantic 校验字符串。"""

    async def run_case() -> None:
        client = FakeStreamingClient(
            [
                [_complete_message("")],
                [
                    ApiTextDeltaEvent(text='{"name":"fixed","score":66}'),
                    _complete_message('{"name":"fixed","score":66}'),
                ],
            ]
        )

        result = await call_structured_json(
            client,
            "model",
            "system",
            "user",
            ExampleResult,
            max_retries=2,
        )

        assert result == ExampleResult(name="fixed", score=66)
        assert "empty response" in client.requests[1].messages[-1].text

    asyncio.run(run_case())


def test_call_structured_json_retries_concise_output_after_token_limit() -> None:
    """模型因输出预算耗尽且没有可见文本时，应收到截断提示。"""

    async def run_case() -> None:
        client = FakeStreamingClient(
            [
                [_complete_message("", stop_reason="max_tokens")],
                [
                    ApiTextDeltaEvent(text='{"name":"fixed","score":66}'),
                    _complete_message('{"name":"fixed","score":66}'),
                ],
            ]
        )

        result = await call_structured_json(
            client,
            "model",
            "system",
            "user",
            ExampleResult,
            max_retries=2,
        )

        assert result == ExampleResult(name="fixed", score=66)
        assert "output token limit" in client.requests[1].messages[-1].text
        assert client.requests[0].max_tokens == 4096
        assert client.requests[1].max_tokens == 8192

    asyncio.run(run_case())
