from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.cover_letter.prompt import (
    build_cover_letter_system_prompt,
    build_cover_letter_user_prompt,
)
from apps.jd_profile.service import (
    _get_active_provider_config,
    get_resume_jd_source,
    wait_for_ready_profile,
)
from chiren_backend.platform.db import async_session
from chiren_backend.platform.llm import get_client
from chiren_backend.platform.llm.client import ApiMessageRequest, ApiTextDeltaEvent
from chiren_backend.platform.models import (
    CoverLetterGenerationBatch,
    Resume,
    ResumeSection,
    utc_now,
)
from chiren_backend.platform.task_state import (
    cleanup_task,
    create_task,
    update_task_error,
    update_task_result,
    update_task_status,
)
from chiren_backend.platform.work_records import (
    build_work_record,
    find_work_by_meta,
    update_work_status,
)
from shared.types.cover_letter import (
    CoverLetterBatchSchema,
    CoverLetterGenerationParams,
)
from shared.types.jd_profile import JD_PROFILE_SCHEMA_VERSION
from shared.types.messages import ConversationMessage
from shared.types.resume import ResumeSectionSchema
from shared.types.task import TaskStatus, TaskType

log = logging.getLogger(__name__)


def extract_personal_info(
    sections: list[ResumeSectionSchema],
) -> tuple[str, str, str]:
    """从简历区块中提取求职信签名所需的个人信息。"""
    full_name = ""
    email = ""
    phone = ""
    for section in sections:
        if section.type != "personal_info" or not section.content:
            continue
        content_data = (
            section.content
            if isinstance(section.content, dict)
            else section.content.model_dump()
            if hasattr(section.content, "model_dump")
            else {}
        )
        personal_info = content_data.get("personal_info") or content_data
        full_name = (
            personal_info.get("full_name") or personal_info.get("fullName") or ""
        )
        email = personal_info.get("email") or ""
        phone = personal_info.get("phone") or ""
    return full_name, email, phone


def _resume_content_hash(sections: list[ResumeSection]) -> str:
    payload = [
        {
            "id": section.id,
            "type": section.type,
            "title": section.title,
            "visible": section.visible,
            "content": json.loads(section.content or "{}"),
        }
        for section in sections
    ]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def create_cover_letter_task(
    db: AsyncSession,
    resume: Resume,
    params: CoverLetterGenerationParams,
    background_tasks: BackgroundTasks,
) -> tuple[str, CoverLetterGenerationBatch]:
    source = get_resume_jd_source(resume)
    if source is None:
        raise ValueError("当前子简历缺少岗位描述，无法生成求职信")
    _, _, source_hash = source
    sections_result = await db.execute(
        select(ResumeSection).where(ResumeSection.resume_id == resume.id)
    )
    sections = list(sections_result.scalars().all())
    resume_hash = _resume_content_hash(sections)

    existing = await find_work_by_meta(
        db,
        TaskType.COVER_LETTER_GENERATE,
        "resume_id",
        resume.id,
        statuses=(TaskStatus.PENDING, TaskStatus.RUNNING),
    )
    if existing is not None and existing.meta_info.get("source_hash") == source_hash:
        batch = await db.get(
            CoverLetterGenerationBatch, existing.meta_info.get("batch_id")
        )
        if batch is not None:
            log.info(
                "cover_letter.generate_deduplicated resume_id=%s batch_id=%s",
                resume.id,
                batch.id,
            )
            return existing.id, batch

    batch_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    batch = CoverLetterGenerationBatch(
        id=batch_id,
        resume_id=resume.id,
        workspace_id=resume.workspace_id,
        source_hash=source_hash,
        resume_content_hash=resume_hash,
        profile_schema_version=JD_PROFILE_SCHEMA_VERSION,
        params_json=params.model_dump_json(),
        status="pending",
    )
    db.add(batch)
    db.add(
        build_work_record(
            task_id,
            TaskType.COVER_LETTER_GENERATE,
            {
                "batch_id": batch_id,
                "resume_id": resume.id,
                "workspace_id": resume.workspace_id,
                "source_hash": source_hash,
                "style": params.style,
                "language": params.language,
                "length": params.length,
            },
        )
    )
    await db.commit()
    create_task(task_id, TaskType.COVER_LETTER_GENERATE)
    background_tasks.add_task(run_cover_letter_task, task_id, batch_id)
    log.info(
        "cover_letter.generate_requested resume_id=%s batch_id=%s source_hash=%s profile_status=unknown",
        resume.id,
        batch_id,
        source_hash,
    )
    return task_id, batch


async def run_cover_letter_task(task_id: str, batch_id: str) -> None:
    async with async_session() as db:
        batch: CoverLetterGenerationBatch | None = None
        try:
            await update_work_status(db, task_id, TaskStatus.RUNNING)
            await update_task_status(task_id, TaskStatus.RUNNING)
            batch = await db.get(CoverLetterGenerationBatch, batch_id)
            if batch is None:
                raise ValueError("求职信生成批次不存在")
            resume = await db.get(Resume, batch.resume_id)
            if resume is None or resume.workspace_id is None:
                raise ValueError("子简历不存在")

            source = get_resume_jd_source(resume)
            if source is None or source[2] != batch.source_hash:
                batch.status = "obsolete"
                batch.updated_at = utc_now()
                await db.commit()
                raise ValueError("JD 已发生变化，请重新生成求职信")

            sections_result = await db.execute(
                select(ResumeSection).where(ResumeSection.resume_id == resume.id)
            )
            sections = list(sections_result.scalars().all())
            if _resume_content_hash(sections) != batch.resume_content_hash:
                batch.status = "obsolete"
                batch.updated_at = utc_now()
                await db.commit()
                raise ValueError("简历内容已发生变化，请重新生成求职信")

            log.info(
                "cover_letter.profile_wait resume_id=%s batch_id=%s source_hash=%s",
                resume.id,
                batch.id,
                batch.source_hash,
            )
            profile_record = await wait_for_ready_profile(
                db,
                resume,
                trigger="cover_letter_generation",
            )
            profile = profile_record.to_pydantic().profile
            if profile is None:
                raise ValueError("JD Profile 没有可用内容")
            batch.profile_id = profile_record.id
            batch.profile_schema_version = profile_record.schema_version

            provider = await _get_active_provider_config(db)
            if provider is None:
                raise ValueError("请先在设置中配置 AI 提供商")
            client = get_client(
                provider.provider_type, provider.api_key, provider.base_url
            )
            params = CoverLetterGenerationParams.model_validate(
                json.loads(batch.params_json or "{}")
            )
            full_name, email, phone = extract_personal_info(
                [section.to_pydantic() for section in sections if section.visible]
            )
            message = [
                ConversationMessage.from_user_text(
                    build_cover_letter_user_prompt(
                        [
                            section.to_pydantic()
                            for section in sections
                            if section.visible
                        ],
                        source[0],
                        profile,
                        full_name,
                        email,
                        phone,
                        params.company_name,
                        params.recipient_name,
                        params.additional_instructions,
                    )
                )
            ]
            content_parts: list[str] = []
            async for event in client.stream_message(
                ApiMessageRequest(
                    model=provider.model,
                    messages=message,
                    system_prompt=build_cover_letter_system_prompt(
                        params.style, params.language, params.length
                    ),
                    temperature=0.5,
                    max_tokens=16384,
                )
            ):
                if isinstance(event, ApiTextDeltaEvent) and not event.is_think:
                    content_parts.append(event.text)
            content = "".join(content_parts).strip()
            if not content:
                raise ValueError("模型未返回求职信内容")

            batch.generated_content = content
            batch.edited_content = None
            batch.status = "success"
            batch.error_message = None
            batch.updated_at = utc_now()
            await db.commit()
            await update_work_status(db, task_id, TaskStatus.SUCCESS)
            await update_task_result(
                task_id,
                {"batch_id": batch.id, "resume_id": resume.id},
            )
            log.info(
                "cover_letter.generation_succeeded resume_id=%s batch_id=%s profile_id=%s content_length=%s",
                resume.id,
                batch.id,
                batch.profile_id,
                len(content),
            )
            asyncio.create_task(cleanup_task(task_id, None))
        except Exception as exc:
            await db.rollback()
            if batch is not None:
                batch = await db.get(CoverLetterGenerationBatch, batch_id)
            if batch is not None and batch.status != "obsolete":
                batch.status = "error"
                batch.error_message = str(exc)
                batch.updated_at = utc_now()
                await db.commit()
            await update_work_status(db, task_id, TaskStatus.ERROR, str(exc))
            await update_task_error(task_id, str(exc))
            log.exception(
                "cover_letter.generation_failed task_id=%s batch_id=%s",
                task_id,
                batch_id,
            )
            asyncio.create_task(cleanup_task(task_id, None))


async def list_cover_letter_batches(
    db: AsyncSession, resume_id: str
) -> list[CoverLetterBatchSchema]:
    resume = await db.get(Resume, resume_id)
    if resume is None or resume.workspace_id is None:
        raise ValueError("子简历不存在")
    source = get_resume_jd_source(resume)
    current_source_hash = source[2] if source is not None else None
    sections_result = await db.execute(
        select(ResumeSection).where(ResumeSection.resume_id == resume_id)
    )
    current_resume_hash = _resume_content_hash(list(sections_result.scalars().all()))
    result = await db.execute(
        select(CoverLetterGenerationBatch)
        .where(CoverLetterGenerationBatch.resume_id == resume_id)
        .order_by(CoverLetterGenerationBatch.created_at.desc())
    )
    batches = list(result.scalars().all())
    changed = False
    for batch in batches:
        if batch.status == "success" and (
            batch.source_hash != current_source_hash
            or batch.resume_content_hash != current_resume_hash
        ):
            batch.status = "obsolete"
            batch.updated_at = utc_now()
            changed = True
    if changed:
        await db.commit()
    return [batch.to_pydantic() for batch in batches]


async def update_cover_letter_batch(
    db: AsyncSession, batch_id: str, content: str
) -> CoverLetterBatchSchema:
    batch = await db.get(CoverLetterGenerationBatch, batch_id)
    if batch is None:
        raise ValueError("求职信生成批次不存在")
    if batch.status != "success":
        raise ValueError("只有已完成的求职信可以编辑")
    batch.edited_content = content.strip()
    batch.updated_at = utc_now()
    await db.commit()
    await db.refresh(batch)
    log.info("cover_letter.edited batch_id=%s resume_id=%s", batch.id, batch.resume_id)
    return batch.to_pydantic()
