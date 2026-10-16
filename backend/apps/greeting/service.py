from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.greeting.prompt import build_system_prompt, build_user_prompt
from apps.jd_profile.formatting import build_jd_profile_prompt_block
from apps.jd_profile.service import (
    _get_active_provider_config,
    get_resume_jd_source,
    wait_for_ready_profile,
)
from chiren_backend.platform.db import async_session
from chiren_backend.platform.llm import call_structured_json, get_client
from chiren_backend.platform.models import (
    GreetingGenerationBatch,
    JobDescriptionProfile,
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
from shared.types.greeting import GreetingBatchSchema, GreetingGenerationResult
from shared.types.task import TaskStatus, TaskType

log = logging.getLogger(__name__)

GREETING_MAX_TOKENS = 16384


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


def _format_resume_sections(sections: list[ResumeSection]) -> str:
    return json.dumps(
        [
            {
                "section_id": section.id,
                "section_type": section.type,
                "title": section.title,
                "content": json.loads(section.content or "{}"),
            }
            for section in sections
            if section.visible
        ],
        ensure_ascii=False,
        indent=2,
    )


async def create_greeting_task(
    db: AsyncSession,
    resume: Resume,
    background_tasks: Any,
) -> tuple[str, GreetingGenerationBatch]:
    source = get_resume_jd_source(resume)
    if source is None:
        raise ValueError("当前子简历缺少岗位描述，无法生成招呼语")
    _, _, source_hash = source
    sections_result = await db.execute(
        select(ResumeSection)
        .where(ResumeSection.resume_id == resume.id)
        .order_by(ResumeSection.sort_order)
    )
    sections = list(sections_result.scalars().all())
    resume_hash = _resume_content_hash(sections)

    existing = await find_work_by_meta(
        db,
        TaskType.GREETING_GENERATE,
        "resume_id",
        resume.id,
        statuses=(TaskStatus.PENDING, TaskStatus.RUNNING),
    )
    if existing is not None and existing.meta_info.get("source_hash") == source_hash:
        batch = await db.get(GreetingGenerationBatch, existing.meta_info["batch_id"])
        if batch is not None:
            return existing.id, batch

    batch_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    batch = GreetingGenerationBatch(
        id=batch_id,
        resume_id=resume.id,
        workspace_id=resume.workspace_id,
        source_hash=source_hash,
        resume_content_hash=resume_hash,
        status="pending",
    )
    db.add(batch)
    db.add(
        build_work_record(
            task_id,
            TaskType.GREETING_GENERATE,
            {
                "batch_id": batch_id,
                "resume_id": resume.id,
                "workspace_id": resume.workspace_id,
                "source_hash": source_hash,
            },
        )
    )
    await db.commit()
    create_task(task_id, TaskType.GREETING_GENERATE)
    background_tasks.add_task(run_greeting_task, task_id, batch_id)
    return task_id, batch


async def run_greeting_task(task_id: str, batch_id: str) -> None:
    async with async_session() as db:
        try:
            await update_work_status(db, task_id, TaskStatus.RUNNING)
            await update_task_status(task_id, TaskStatus.RUNNING)
            batch = await db.get(GreetingGenerationBatch, batch_id)
            if batch is None:
                raise ValueError("招呼语生成批次不存在")
            resume = await db.get(Resume, batch.resume_id)
            if resume is None:
                raise ValueError("子简历不存在")

            source = get_resume_jd_source(resume)
            if source is None or source[2] != batch.source_hash:
                batch.status = "obsolete"
                await db.commit()
                raise ValueError("JD 已发生变化，请重新生成招呼语")

            profile = await _wait_for_profile(db, resume, batch.source_hash)
            sections_result = await db.execute(
                select(ResumeSection)
                .where(ResumeSection.resume_id == resume.id)
                .order_by(ResumeSection.sort_order)
            )
            sections = list(sections_result.scalars().all())
            current_resume_hash = _resume_content_hash(sections)
            if current_resume_hash != batch.resume_content_hash:
                batch.status = "obsolete"
                await db.commit()
                raise ValueError("简历内容已发生变化，请重新生成招呼语")

            provider = await _get_active_provider_config(db)
            if provider is None:
                raise ValueError("请先在设置中配置 AI 提供商")
            client = get_client(
                provider.provider_type, provider.api_key, provider.base_url
            )
            profile_data = profile.to_pydantic().profile
            if profile_data is None:
                raise ValueError("JD Profile 没有可用内容")
            result = await call_structured_json(
                client,
                provider.model,
                build_system_prompt(),
                build_user_prompt(
                    source[1],
                    source[0],
                    build_jd_profile_prompt_block(profile_data, "greeting"),
                    _format_resume_sections(sections),
                ),
                GreetingGenerationResult,
                max_retries=3,
                max_tokens=GREETING_MAX_TOKENS,
                temperature=0.0,
                post_validator=lambda value: _validate_evidence(value, profile_data),
                invalid_response_prefix="Greeting JSON validation failed",
            )
            batch.status = "success"
            batch.result_json = result.model_dump_json()
            batch.error_message = None
            batch.updated_at = utc_now()
            await db.commit()
            await update_work_status(db, task_id, TaskStatus.SUCCESS)
            await update_task_result(
                task_id, {"batch_id": batch_id, "resume_id": resume.id}
            )
            asyncio.create_task(cleanup_task(task_id, None))
        except Exception as exc:
            await db.rollback()
            batch = await db.get(GreetingGenerationBatch, batch_id)
            if batch is not None and batch.status != "obsolete":
                batch.status = "error"
                batch.error_message = str(exc)
                batch.updated_at = utc_now()
                await db.commit()
            await update_work_status(db, task_id, TaskStatus.ERROR, str(exc))
            await update_task_error(task_id, str(exc))
            asyncio.create_task(cleanup_task(task_id, None))
            log.exception("run_greeting_task error: %s", exc)


async def _wait_for_profile(
    db: AsyncSession, resume: Resume, source_hash: str, timeout: float = 120
) -> JobDescriptionProfile:
    profile = await wait_for_ready_profile(
        db,
        resume,
        trigger="greeting_generation",
        timeout=timeout,
    )
    if profile.source_hash != source_hash:
        raise ValueError("JD 已发生变化，请重新生成招呼语")
    return profile


def _validate_evidence(
    result: GreetingGenerationResult, profile: Any
) -> str | None:
    requirement_ids = {item.id for item in profile.requirements}
    criterion_ids = {item.id for item in profile.core_selection_criteria}
    for variant in result.variants:
        if criterion_ids and variant.selection_criterion_id not in criterion_ids:
            return (
                "Every greeting variant must select selection_criterion_id from "
                "core_selection_criteria[].id. Valid criterion ids: "
                f"{', '.join(sorted(criterion_ids))}"
            )
        for point in variant.match_points:
            if point.requirement_id not in requirement_ids:
                return (
                    f"Unknown requirement_id: {point.requirement_id}. "
                    "match_points[].requirement_id must come from requirements[].id, "
                    "not core_selection_criteria[].id. Valid requirement ids: "
                    f"{', '.join(sorted(requirement_ids))}"
                )
    return None


async def list_greeting_batches(
    db: AsyncSession, resume_id: str
) -> list[GreetingBatchSchema]:
    resume = await db.get(Resume, resume_id)
    source = get_resume_jd_source(resume) if resume is not None else None
    sections_result = await db.execute(
        select(ResumeSection).where(ResumeSection.resume_id == resume_id)
    )
    current_resume_hash = _resume_content_hash(list(sections_result.scalars().all()))
    current_source_hash = source[2] if source is not None else None
    result = await db.execute(
        select(GreetingGenerationBatch)
        .where(GreetingGenerationBatch.resume_id == resume_id)
        .order_by(GreetingGenerationBatch.created_at.desc())
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
    return [item.to_pydantic() for item in batches]
