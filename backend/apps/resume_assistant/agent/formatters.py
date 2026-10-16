import json
from collections.abc import Iterator
from datetime import datetime

from apps.resume_assistant.agent.events import (
    AgentEvent,
    TextDeltaEvent,
    TextStartEvent,
    ThinkingDeltaEvent,
    ThinkingStartEvent,
)
from chiren_backend.platform.llm.client import ApiTextDeltaEvent


class _DateTimeEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，用于序列化 datetime 对象。"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class StreamingFormatter:
    """将 API 文本事件转换为 AgentEvent"""

    def __init__(self):
        self._sent_thinking_start = False
        self._sent_text_start = False

    def format(self, event: ApiTextDeltaEvent) -> Iterator[AgentEvent]:
        """将 API 文本事件转换为 AgentEvent"""
        if event.is_think:
            if not self._sent_thinking_start:
                self._sent_thinking_start = True
                yield ThinkingStartEvent()
            yield ThinkingDeltaEvent(text=event.text)
        else:
            if not self._sent_text_start:
                self._sent_text_start = True
                yield TextStartEvent()
            yield TextDeltaEvent(text=event.text)

    def reset(self):
        """重置状态（每轮迭代开始时调用）"""
        self._sent_thinking_start = False
        self._sent_text_start = False


def to_sse_event(event: AgentEvent) -> dict[str, str]:
    """将 AgentEvent 转换为 SSE 格式"""
    event_type_map = {
        "NextEvent": "next",
        "ThinkingStartEvent": "thinking_start",
        "ThinkingDeltaEvent": "thinking_delta",
        "TextStartEvent": "text_start",
        "TextDeltaEvent": "text_delta",
        "ToolUseEvent": "tool_use",
        "ToolResultEvent": "tool_result",
        "DoneEvent": "done",
        "ErrorEvent": "error",
    }

    event_name = event.__class__.__name__
    event_type = event_type_map.get(event_name, event_name.lower())

    if hasattr(event, "__dict__"):
        data = {k: v for k, v in event.__dict__.items() if v is not None}
    else:
        data = {}

    return {
        "event": event_type,
        "data": json.dumps(data, ensure_ascii=False, cls=_DateTimeEncoder),
    }
