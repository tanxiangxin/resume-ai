import json
import logging
from collections.abc import AsyncIterator
from json import JSONEncoder

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.interview.prompt import (
    build_interview_system_prompt,
    format_sections_for_prompt,
)
from apps.interview.schemas import InterviewChatRequest
from apps.jd_profile.service import ProviderRuntimeConfig, ensure_jd_profile
from chiren_backend.platform.llm.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiTextDeltaEvent,
    SupportsStreamingMessages,
)
from chiren_backend.platform.models import (
    ConversationMessageRecord,
    InterviewCollection,
    InterviewRound,
    Resume,
    ResumeSection,
)
from shared.types.messages import (
    ContentBlock,
    ConversationMessage,
    TextBlock,
)

log = logging.getLogger(__name__)

content_adapter = TypeAdapter(list[ContentBlock])


class _DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        try:
            return obj.isoformat()
        except AttributeError:
            return super().default(obj)


def _sse(event: str, data: dict | None = None) -> dict[str, str]:
    return {
        "event": event,
        "data": json.dumps(data or {}, ensure_ascii=False, cls=_DateTimeEncoder),
    }


async def _load_messages(
    conversation_id: str, db: AsyncSession
) -> list[ConversationMessage]:
    stmt = (
        select(ConversationMessageRecord)
        .where(ConversationMessageRecord.conversation_id == conversation_id)
        .order_by(ConversationMessageRecord.created_at.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    messages: list[ConversationMessage] = []
    for rec in records:
        try:
            content = content_adapter.validate_python(
                json.loads(rec.content) if rec.content else []
            )
        except Exception:
            content = [TextBlock(text=rec.content or "")]
        msg = ConversationMessage(role=rec.role, content=content)
        messages.append(msg)
    return messages


def _build_user_message(action: str, content: str) -> ConversationMessage:
    if action == "start":
        return ConversationMessage.from_user_text("<INTERVIEW_START>")
    elif action == "skip":
        return ConversationMessage.from_user_text("<SKIP>")
    elif action == "hint":
        return ConversationMessage.from_user_text("<HINT>")
    else:
        return ConversationMessage.from_user_text(content)


async def _persist_message(
    conversation_id: str, message: ConversationMessage, db: AsyncSession
) -> None:
    record = ConversationMessageRecord(
        conversation_id=conversation_id,
        role=message.role,
        content=json.dumps(
            [block.model_dump(mode="json") for block in message.content],
            ensure_ascii=False,
        ),
    )
    db.add(record)


async def interview_chat(
    round: InterviewRound,
    request: InterviewChatRequest,
    api_client: SupportsStreamingMessages,
    db: AsyncSession,
) -> AsyncIterator[dict[str, str]]:
    round_id = round.id

    collection_result = await db.execute(
        select(InterviewCollection).where(
            InterviewCollection.id == round.interview_collection_id
        )
    )
    collection = collection_result.scalar_one_or_none()
    if collection is None:
        yield _sse("error", {"message": "面试集合不存在"})
        return
    sub_resume_id = collection.sub_resume_id

    sections_result = await db.execute(
        select(ResumeSection)
        .where(
            ResumeSection.resume_id == sub_resume_id,
            ResumeSection.visible == True,
        )
        .order_by(ResumeSection.sort_order.asc())
    )
    sections_raw = sections_result.scalars().all()
    sections = [s.to_pydantic().model_dump(mode="json") for s in sections_raw]

    resume_result = await db.execute(select(Resume).where(Resume.id == sub_resume_id))
    resume = resume_result.scalar_one_or_none()

    jd_text: str | None = None
    if resume is not None and resume.meta_info:
        jd_text = resume.meta_info.get("job_description")

    if not jd_text:
        yield _sse("error", {"message": "子简历缺少岗位描述(JD)，无法进行面试"})
        return

    jd_profile = None
    if resume is not None:
        provider = ProviderRuntimeConfig(
            provider_type=request.type,
            api_key=request.api_key,
            base_url=request.base_url,
            model=request.model,
        )
        profile_record = await ensure_jd_profile(
            db,
            resume,
            trigger="interview_chat",
            provider_override=provider,
            mode="inline",
            retry_failed=True,
        )
        if profile_record is not None and profile_record.status == "ready":
            jd_profile = profile_record.to_pydantic().profile

    messages = await _load_messages(round_id, db)
    user_msg = _build_user_message(request.action, request.content)
    messages.append(user_msg)

    system_prompt = build_interview_system_prompt(
        round,
        format_sections_for_prompt(sections),
        jd_text,
        jd_profile,
    )

    api_request = ApiMessageRequest(
        model=request.model,
        messages=messages,
        system_prompt=system_prompt,
        max_tokens=4096,
        temperature=0.7,
    )

    try:
        yield _sse("next")

        sent_thinking = False
        sent_text = False
        complete_event: ApiMessageCompleteEvent | None = None

        async for api_event in api_client.stream_message(api_request):
            if isinstance(api_event, ApiTextDeltaEvent):
                if api_event.is_think:
                    if not sent_thinking:
                        sent_thinking = True
                        yield _sse("thinking_start")
                    yield _sse("thinking_delta", {"text": api_event.text})
                else:
                    if not sent_text:
                        sent_text = True
                        yield _sse("text_start")
                    yield _sse("text_delta", {"text": api_event.text})
            elif isinstance(api_event, ApiMessageCompleteEvent):
                complete_event = api_event

        if complete_event is None:
            yield _sse("error", {"message": "API 未返回有效响应"})
            return

        await _persist_message(round_id, user_msg, db)
        await _persist_message(round_id, complete_event.message, db)
        await db.commit()

        yield _sse("done")

    except Exception as e:
        log.exception("Interview chat error: %s", e)
        yield _sse("error", {"message": str(e)})
