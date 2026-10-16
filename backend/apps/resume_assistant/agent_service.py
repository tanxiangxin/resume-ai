import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette import EventSourceResponse

from apps.resume_assistant.agent.runtime import AgentRuntime
from apps.resume_assistant.agent.state import IterationState
from apps.resume_assistant.conversation_store import ConversationStore
from apps.resume_assistant.prompt import SUB_SYSTEM, SYSTEM, build_sections_prompt
from apps.resume_assistant.schemas import ResumeAssistantRequest
from apps.resume_assistant.tools import (
    AddSectionTool,
    SectionInfoTool,
    UpdateSectionTool,
)
from chiren_backend.platform.llm import get_client
from chiren_backend.platform.models import Resume
from shared.types.base_tool import ToolRegistry
from shared.types.messages import ConversationMessage
from shared.types.resume import ResumeSectionSchema

log = logging.getLogger(__name__)


async def resume_assistant_service(
    request: ResumeAssistantRequest,
    resume: Resume,
    sections: list[ResumeSectionSchema],
    db: AsyncSession,
) -> EventSourceResponse:
    sections_list: list[dict[str, Any]] = []
    id_to_type: dict[str, str] = {}

    for section in sections:
        id_to_type[section.id] = section.type
        sections_list.append(section.model_dump())

    return EventSourceResponse(
        generate_content(request, resume, sections_list, id_to_type, db)
    )


async def generate_content(
    request: ResumeAssistantRequest,
    resume: Resume,
    sections: list[dict[str, Any]],
    id_to_type: dict[str, str],
    db: AsyncSession,
):
    store = ConversationStore()
    messages: list[ConversationMessage] = store.read(request.resume_id)
    messages.append(ConversationMessage.from_user_text(request.input))

    initial_state = IterationState(
        messages=messages,
    )

    tool_registry = ToolRegistry()
    for tool in (
        UpdateSectionTool(),
        AddSectionTool(),
        SectionInfoTool(),
    ):
        tool_registry.register(tool)

    runtime = AgentRuntime(
        db=db,
        store=store,
        api_client=get_client(request.type, request.api_key, request.base_url),
        tool_registry=tool_registry,
        model=request.model,
    )

    async for event in runtime.execute(
        request=request,
        initial_state=initial_state,
        sections=sections,
        system_template=SYSTEM,
        sub_system_template=SUB_SYSTEM,
        build_sections_prompt_fn=build_sections_prompt,
        id_to_type=id_to_type,
        resume=resume,
    ):
        yield event
