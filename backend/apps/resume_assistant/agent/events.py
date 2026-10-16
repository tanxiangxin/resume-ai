from dataclasses import dataclass

from shared.types.messages import ConversationMessage


@dataclass
class NextEvent:
    """事件类型：next

    触发条件：每次 while 循环迭代开始时（count < max_count 时）
    触发时机：在调用 client.stream_message() 之前发射
    语义：通知客户端开始一个新的对话轮次
    """

    pass


@dataclass
class ThinkingStartEvent:
    """事件类型：thinking_start

    触发条件：当收到第一个 ApiTextDeltaEvent 且 event.is_think == True 时
    触发时机：在该轮次首次收到 thinking 类型 delta 事件之前
    前置条件：sended_think == False（同一轮次仅发射一次）
    语义：通知客户端开始流式传输 AI 思考过程
    """

    pass


@dataclass
class ThinkingDeltaEvent:
    """事件类型：thinking_delta

    触发条件：每个 ApiTextDeltaEvent 且 event.is_think == True
    语义：流式传输 AI 思考过程的文本片段
    顺序规则：必须在 thinking_start 之后，thinking_start 之前不会发射
    """

    text: str


@dataclass
class TextStartEvent:
    """事件类型：text_start

    触发条件：当收到第一个 ApiTextDeltaEvent 且 event.is_think == False 时
    触发时机：在该轮次首次收到非 thinking 类型 delta 事件之前
    前置条件：sended_text == False（同一轮次仅发射一次）
    语义：通知客户端开始流式传输正式回复文本
    """

    pass


@dataclass
class TextDeltaEvent:
    """事件类型：text_delta

    触发条件：每个 ApiTextDeltaEvent 且 event.is_think == False
    语义：流式传输正式回复的文本片段
    顺序规则：必须在 text_start 之后，text_start 之前不会发射
    """

    text: str


@dataclass
class ToolUseEvent:
    """事件类型：tool_use

    触发条件：遍历 tool_use_blocks 中的每个 ToolUseBlock 时
    语义：通知客户端即将执行一个工具调用
    """

    name: str
    id: str
    input: dict


@dataclass
class ToolResultEvent:
    """事件类型：tool_result

    触发条件：工具执行完成后（无论成功或失败）
    语义：向客户端返回工具执行结果
    """

    is_error: bool
    tool_use_id: str
    content: str
    section_content: dict | None = None


@dataclass
class DoneEvent:
    """事件类型：done

    触发条件：
      - 条件A：complete_event is None（API 未返回有效响应）
      - 条件B：complete_event.stop_reason in ("end_turn", "stop")
    语义：通知客户端本轮对话成功结束
    注意：发射后 while 循环 break，整个生成流程结束
    """

    pass


@dataclass
class ErrorEvent:
    """事件类型：error

    触发条件：except Exception as e 捕获任何异常时
    语义：通知客户端发生错误，生成流程终止
    副作用：会调用 store.extend(request.resume_id, pending) 保存 pending 消息
    """

    message: str


@dataclass
class AssistantMessageEvent:
    """事件类型：assistant_message

    触发条件：API 返回完整 assistant 消息时
    语义：通知外部新的 assistant 消息已生成，用于持久化
    """

    message: ConversationMessage


@dataclass
class ToolResultMessageEvent:
    """事件类型：tool_result_message

    触发条件：工具调用结果作为 user 消息追加到 state.messages 时
    语义：通知外部新的 tool_result 消息已生成，用于持久化
    """

    message: ConversationMessage


@dataclass
class MessagesCompactedEvent:
    """事件类型：messages_compacted

    触发条件：auto_compact 发生，messages 被重写时
    语义：通知外部 compact 已发生，用于追踪/日志
    """


AgentEvent = (
    NextEvent
    | ThinkingStartEvent
    | ThinkingDeltaEvent
    | TextStartEvent
    | TextDeltaEvent
    | ToolUseEvent
    | ToolResultEvent
    | DoneEvent
    | ErrorEvent
)


InternalEvent = AssistantMessageEvent | ToolResultMessageEvent | MessagesCompactedEvent
