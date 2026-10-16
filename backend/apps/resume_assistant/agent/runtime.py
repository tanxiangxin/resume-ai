import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.jd_profile.formatting import build_jd_profile_prompt_block
from apps.jd_profile.service import get_resume_jd_source
from apps.resume_assistant.agent.context import QueryContext
from apps.resume_assistant.agent.core import (
    AgentCore,
    BuildSectionsPromptFn,
    InternalEvent,
    ToolExecutor,
)
from apps.resume_assistant.agent.events import (
    AgentEvent,
    AssistantMessageEvent,
    MessagesCompactedEvent,
    ToolResultEvent,
    ToolResultMessageEvent,
)
from apps.resume_assistant.agent.formatters import to_sse_event
from apps.resume_assistant.agent.state import IterationState
from apps.resume_assistant.conversation_store import ConversationStore
from apps.resume_assistant.prompt import build_jd_prompt
from apps.resume_assistant.schemas import ResumeAssistantRequest
from chiren_backend.platform.llm.client import SupportsStreamingMessages
from chiren_backend.platform.models import (
    ConversationMessageRecord,
    JobDescriptionAnalysis,
    JobDescriptionProfile,
    Resume,
)
from shared.types.base_tool import ToolExecutionContext, ToolRegistry
from shared.types.messages import ConversationMessage, ToolResultBlock, ToolUseBlock

log = logging.getLogger(__name__)


def create_tool_executor(
    tool_registry: ToolRegistry,
    id_to_type: dict[str, str],
) -> ToolExecutor:
    async def tool_executor(
        tool_use: ToolUseBlock,
        sections: list[dict[str, Any]],
        context: QueryContext,
    ) -> tuple[ToolResultEvent, ToolResultBlock, dict | None]:
        tool_id = tool_use.id
        handler = tool_registry.get(tool_use.name)
        if handler is None:
            result_content = f"Unknown tool: {tool_use.name}"
            return (
                ToolResultEvent(
                    is_error=True, tool_use_id=tool_id, content=result_content
                ),
                ToolResultBlock(
                    tool_use_id=tool_id, content=result_content, is_error=True
                ),
                None,
            )

        try:
            arguments = handler.input_model.model_validate(tool_use.input)
        except ValidationError as e:
            errors = []
            for err in e.errors():
                field = ".".join(str(loc) for loc in err["loc"])
                errors.append(f"  - {field}: {err['msg']}")
            error_msg = "Validation failed:\n" + "\n".join(errors)
            return (
                ToolResultEvent(is_error=True, tool_use_id=tool_id, content=error_msg),
                ToolResultBlock(tool_use_id=tool_id, content=error_msg, is_error=True),
                None,
            )

        client = context.api_client
        model_name = context.model

        tool_result = await handler.execute(
            arguments,
            ToolExecutionContext(
                sections=sections,
                metadata={
                    "tool_use_id": tool_use.id,
                    "id_to_type": id_to_type,
                    "client": client,
                    "model": model_name,
                },
            ),
        )

        section_content = None
        if tool_use.name == "update_section":
            for section in sections:
                if section["id"] == tool_use.input["section_id"]:
                    section_content = {"data": section["content"], "id": section["id"]}
                    break
        elif tool_use.name == "add_section":
            for section in sections:
                if (
                    section["type"] == tool_use.input["type"]
                    and section["title"] == tool_use.input["title"]
                ):
                    section_content = {**section}
                    break

        result_event = ToolResultEvent(
            is_error=tool_result.is_error,
            tool_use_id=tool_id,
            content=tool_result.output,
            section_content=section_content,
        )
        result_block = ToolResultBlock(
            tool_use_id=tool_id,
            content=tool_result.output,
            is_error=tool_result.is_error,
        )

        return (result_event, result_block, section_content)

    return tool_executor


class AgentRuntime:
    def __init__(
        self,
        db: AsyncSession,
        store: ConversationStore,
        api_client: SupportsStreamingMessages,
        tool_registry: ToolRegistry,
        model: str,
        max_tokens: int | None = None,
        temperature: float = 1.0,
        max_iterations: int = 30,
        stop_reasons: set[str] | None = None,
    ):
        self.db = db
        self.store = store
        self.api_client = api_client
        self.tool_registry = tool_registry
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.stop_reasons = stop_reasons or {"end_turn", "stop"}

    async def execute(
        self,
        request: ResumeAssistantRequest,
        initial_state: IterationState,
        sections: list[dict[str, Any]],
        system_template: str,
        sub_system_template: str | None,
        build_sections_prompt_fn: BuildSectionsPromptFn,
        id_to_type: dict[str, str],
        resume: Resume | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        system_suffix: str | None = None

        if resume is not None and resume.meta_info:
            job_description = resume.meta_info.get("job_description")
            if job_description:
                parts: list[str] = [
                    sub_system_template.format(job_description=job_description)
                ]
            else:
                parts = []

            source = get_resume_jd_source(resume)
            profile_context: str | None = None
            if source is not None:
                result = await self.db.execute(
                    select(JobDescriptionProfile)
                    .where(
                        JobDescriptionProfile.resume_id == resume.id,
                        JobDescriptionProfile.source_hash == source[2],
                        JobDescriptionProfile.status == "ready",
                    )
                    .limit(1)
                )
                jd_profile = result.scalars().first()
                if jd_profile is not None:
                    profile_data = jd_profile.to_pydantic().profile
                    if profile_data is not None:
                        profile_context = build_jd_profile_prompt_block(
                            profile_data, "resume"
                        )

            result = await self.db.execute(
                select(JobDescriptionAnalysis)
                .where(JobDescriptionAnalysis.resume_id == resume.id)
                .order_by(JobDescriptionAnalysis.created_at.desc())
                .limit(1)
            )
            jd_analysis = result.scalars().first()
            if jd_analysis is not None:
                parts.append(build_jd_prompt(jd_analysis.to_pydantic(), sections))
            elif profile_context is not None:
                parts.append(profile_context)

            if parts:
                system_suffix = "\n\n" + "\n\n".join(parts)

        context = QueryContext(
            api_client=self.api_client,
            tool_registry=self.tool_registry,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            max_iterations=self.max_iterations,
            stop_reasons=self.stop_reasons,
            metadata={},
        )

        tool_executor_fn = create_tool_executor(
            tool_registry=self.tool_registry,
            id_to_type=id_to_type,
        )

        core = AgentCore(context=context, tool_executor=tool_executor_fn)
        pending: list[ConversationMessage] = []

        if initial_state.messages[-1].role == "user":
            pending.append(initial_state.messages[-1])

        try:
            async for event in core.run(
                initial_state=initial_state,
                sections=sections,
                system_template=system_template,
                system_suffix=system_suffix,
                build_sections_prompt_fn=build_sections_prompt_fn,
            ):
                if isinstance(event, InternalEvent):
                    if isinstance(event, MessagesCompactedEvent):
                        pending = pending[-6:]
                        self.store.write(request.resume_id, initial_state.messages[:1])
                    else:
                        self._handle_internal_event(event, request.resume_id, pending)
                elif isinstance(event, AgentEvent):
                    yield to_sse_event(event)

        finally:
            self.store.extend(request.resume_id, pending)
            await self.db.commit()

    def _handle_internal_event(
        self, event: InternalEvent, resume_id: str, pending: list[ConversationMessage]
    ) -> None:
        if isinstance(event, (AssistantMessageEvent, ToolResultMessageEvent)):
            self.db.add(
                ConversationMessageRecord(
                    conversation_id=resume_id,
                    role=event.message.role,
                    content=json.dumps(
                        [
                            block.model_dump(mode="json")
                            for block in event.message.content
                        ],
                        ensure_ascii=False,
                    ),
                )
            )
            pending.append(event.message)
