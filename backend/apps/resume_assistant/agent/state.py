from dataclasses import dataclass, field

from shared.types.messages import ConversationMessage


@dataclass
class IterationState:
    messages: list[ConversationMessage] = field(default_factory=list)
    resume_info: str = ""
    system: str = ""
    tools_schema: list[dict] = field(default_factory=list)
    count: int = 0
    _cached_resume_info: str | None = None
