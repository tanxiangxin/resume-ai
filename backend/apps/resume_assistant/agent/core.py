"""AgentCore - 纯函数，循环控制，无任何 I/O"""

import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from apps.resume_assistant.agent.compact import auto_compact_if_needed
from apps.resume_assistant.agent.context import QueryContext
from apps.resume_assistant.agent.events import (
    AgentEvent,
    AssistantMessageEvent,
    DoneEvent,
    ErrorEvent,
    InternalEvent,
    MessagesCompactedEvent,
    NextEvent,
    ToolResultEvent,
    ToolResultMessageEvent,
    ToolUseEvent,
)
from apps.resume_assistant.agent.formatters import StreamingFormatter
from apps.resume_assistant.agent.state import IterationState
from chiren_backend.platform.llm.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiTextDeltaEvent,
)
from shared.types.messages import ConversationMessage, ToolResultBlock, ToolUseBlock

log = logging.getLogger(__name__)

ToolExecutor = Callable[
    [ToolUseBlock, list[dict[str, Any]], QueryContext],
    Awaitable[tuple[ToolResultEvent, ToolResultBlock, dict | None]],
]


def make_current_resume_info(sections: list[dict[str, Any]]) -> str:
    """计算当前 resume 的缓存 key（JSON 序列化）"""

    def json_serializer(obj: Any) -> Any:
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return json.dumps(sections, ensure_ascii=False, default=json_serializer, indent=2)


def insert_resume_info(
    messages: list[ConversationMessage],
    resume_info: str,
    count: int,
) -> list[ConversationMessage]:
    """在最后一条消息中插入 resume_info"""
    from shared.types.messages import ConversationMessage, ToolResultBlock

    if not messages:
        return messages

    last_msg = messages[-1]

    if count == 1 and last_msg.role == "user":
        return [
            *messages[:-1],
            ConversationMessage.from_user_text(
                f"Below is the current resume information in JSON format:\n\n"
                f"<resume_info>\n{resume_info}\n</resume_info>"
            ),
            messages[-1],
        ]
    elif (
        count != 1
        and last_msg.role == "user"
        and last_msg.content
        and isinstance(last_msg.content[-1], ToolResultBlock)
    ):
        last_block = last_msg.content[-1]
        new_block = last_block.model_copy(
            update={
                "content": (
                    f"{last_block.content}\n\n"
                    f"Below is the current resume information in JSON format:\n\n"
                    f"<resume_info>\n{resume_info}\n</resume_info>"
                )
            }
        )
        new_last = last_msg.model_copy(
            update={"content": [*last_msg.content[:-1], new_block]}
        )
        return [*messages[:-1], new_last]

    return messages


BuildSectionsPromptFn = Callable[[list[dict[str, Any]]], str]


class AgentCore:
    """AgentCore - 循环控制逻辑"""

    def __init__(self, context: QueryContext, tool_executor: ToolExecutor):
        self.context = context
        self.tool_executor = tool_executor

    async def run(
        self,
        initial_state: IterationState,
        sections: list[dict[str, Any]],
        system_template: str,
        system_suffix: str | None,
        build_sections_prompt_fn: BuildSectionsPromptFn,
    ) -> AsyncIterator[AgentEvent | InternalEvent]:
        """运行主循环，直到达到停止条件或最大迭代次数。

        Args:
            initial_state: 初始迭代状态，包含 messages 等。
            sections: 简历 sections 列表。
            system_template: system prompt 模板，其中包含 ``{sections}`` 占位符。
            system_suffix: system prompt 后缀（包含 JD 子系统提示和 JD 分析结果），可为 None。
            build_sections_prompt_fn: 构建 sections prompt 的函数。

        Yields:
            AgentEvent | InternalEvent: 各类事件，按顺序包括：
                - NextEvent: 标记新一轮迭代开始。
                - StreamingFormatter 产生的文本/思考事件：API 流式响应片段。
                - ToolUseEvent: 工具调用事件。
                - ToolResultEvent: 工具结果事件。
                - DoneEvent: 正常结束事件。
                - ErrorEvent: 异常结束事件。
                - AssistantMessageEvent: 内部事件，新 assistant 消息已生成。
                - ToolResultMessageEvent: 内部事件，新 tool_result 消息已生成。
                - MessagesCompactedEvent: 内部事件，compact 发生了。
        """
        state = initial_state
        formatter = StreamingFormatter()

        while state.count < self.context.max_iterations:
            state.count += 1
            formatter.reset()

            resume_info = make_current_resume_info(sections)

            if resume_info != state._cached_resume_info:
                state._cached_resume_info = resume_info

                sections_prompt = build_sections_prompt_fn(sections)
                system = system_template.format(sections=sections_prompt)
                if system_suffix:
                    system += system_suffix

                state.system = system
                state.tools_schema = self.context.tool_registry.to_api_schema_v2(
                    sections
                )

            state.messages, was_compacted = await auto_compact_if_needed(
                state.messages,
                api_client=self.context.api_client,
                model=self.context.model,
                system_prompt=state.system,
            )
            if was_compacted:
                yield MessagesCompactedEvent()

            state.messages = insert_resume_info(
                state.messages, resume_info, state.count
            )

            api_request = ApiMessageRequest(
                model=self.context.model,
                messages=state.messages,
                system_prompt=state.system,
                tools=state.tools_schema,
                max_tokens=self.context.max_tokens,
                temperature=self.context.temperature,
            )

            yield NextEvent()

            complete_event = None
            try:
                async for api_event in self.context.api_client.stream_message(
                    api_request
                ):
                    if isinstance(api_event, ApiTextDeltaEvent):
                        for agent_event in formatter.format(api_event):
                            yield agent_event
                    elif isinstance(api_event, ApiMessageCompleteEvent):
                        complete_event = api_event
            except Exception as e:
                log.error(f"Agent loop error: {e}")
                yield ErrorEvent(message=str(e))
                break

            if complete_event is None:
                yield DoneEvent()
                break

            state.messages.append(complete_event.message)
            yield AssistantMessageEvent(message=complete_event.message)

            if complete_event.message.tool_uses:
                async for event in self._handle_tool_calls(
                    complete_event.message.tool_uses,
                    state,
                    sections,
                ):
                    yield event

                yield ToolResultMessageEvent(message=state.messages[-1])

            if complete_event.stop_reason in self.context.stop_reasons:
                yield DoneEvent()
                break

    async def _handle_tool_calls(
        self,
        tool_use_blocks: list[ToolUseBlock],
        state: IterationState,
        sections: list[dict[str, Any]],
    ) -> AsyncIterator[AgentEvent]:
        """处理工具调用

        Args:
            tool_use_blocks: 工具调用列表
            state: 当前迭代状态
            sections: 简历 sections

        Yields:
            AgentEvent: 工具相关事件
        """
        from shared.types.messages import ConversationMessage, ToolResultBlock

        tool_results: list[ToolResultBlock] = []

        for tool_use in tool_use_blocks:
            tool_id = tool_use.id

            yield ToolUseEvent(
                name=tool_use.name,
                id=tool_id,
                input=tool_use.input,
            )

            tool_result_event, tool_result_block, _ = await self.tool_executor(
                tool_use, sections, self.context
            )

            yield tool_result_event
            tool_results.append(tool_result_block)

        if tool_results:
            tool_result_msg = ConversationMessage(
                role="user",
                content=tool_results,
            )
            state.messages.append(tool_result_msg)
