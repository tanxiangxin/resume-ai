from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.config.schemas import ProviderConfig
from chiren_backend.platform.llm import (
    SupportsStreamingMessages,
    call_structured_json,
    get_client,
)
from chiren_backend.platform.models import (
    BaseWork,
    JobDescriptionProfile,
    Resume,
    UserConfig,
    utc_now,
)
from chiren_backend.platform.task_state import (
    cleanup_task,
    create_task,
    update_task_error,
    update_task_result,
    update_task_status,
)
from chiren_backend.platform.work_records import build_work_record, update_work_status
from shared.types.jd_profile import (
    JD_PROFILE_SCHEMA_VERSION,
    CurrentJdProfileResponse,
    JdProfileData,
    JdProfileExtractionResult,
    JdProfileResponsibilitiesResult,
    JdProfileRoleResult,
    JdProfileSignalsResult,
    JdProfileSource,
    JdProfileStrategyResult,
)
from shared.types.strict_model import StrictBaseModel
from shared.types.task import TaskStatus, TaskType

log = logging.getLogger(__name__)

PROVIDER_CONFIG_KEY = "provider_config"
MAX_RETRIES = 3
PROFILE_CHUNK_CONCURRENCY = 4
PROFILE_CHUNK_MAX_TOKENS = 16384

_JD_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "responsibilities": (
        "工作职责",
        "岗位职责",
        "工作内容",
        "职责",
        "responsibilities",
        "responsibility",
        "duties",
        "what you will do",
        "what youll do",
        "role responsibilities",
    ),
    "anti_fit": (
        "什么样的人可能不太适合",
        "不太适合",
        "不适合",
        "who is not a fit",
        "not a fit",
        "not suitable",
        "what we do not want",
        "what we don't want",
    ),
    "selection": (
        "团队当前方向",
        "我们希望你是什么样的人",
        "任职要求",
        "我们在寻找",
        "我们更看重",
        "what we look for",
        "what we care about",
        "ideal candidate",
        "requirements",
        "qualifications",
        "who you are",
    ),
}

_PRODUCT_SIGNAL_MARKERS = (
    "产品意识",
    "产品体验",
    "产品价值",
    "用户体验",
    "用户价值",
    "用户意味着",
    "product sense",
    "product experience",
    "user experience",
    "user impact",
    "user value",
    "trade-off",
    "tradeoff",
)


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    provider_type: Literal["openai", "anthropic"]
    base_url: str
    api_key: str
    model: str


def normalize_jd_source(job_description: str, job_title: str | None = None) -> str:
    title = re.sub(r"\s+", " ", (job_title or "").strip())
    body = re.sub(r"\s+", " ", job_description.strip())
    return f"title:{title}\nbody:{body}"


def calculate_jd_source_hash(job_description: str, job_title: str | None = None) -> str:
    normalized = normalize_jd_source(job_description, job_title)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_resume_jd_source(resume: Resume) -> tuple[str, str | None, str] | None:
    meta_info = resume.meta_info or {}
    job_description = str(meta_info.get("job_description") or "").strip()
    if not job_description:
        return None
    job_title = meta_info.get("job_title")
    if isinstance(job_title, str):
        job_title = job_title.strip() or None
    else:
        job_title = None
    source_hash = calculate_jd_source_hash(job_description, job_title)
    return job_description, job_title, source_hash


async def parse_jd_profile(
    client: SupportsStreamingMessages,
    model: str,
    job_description: str,
    job_title: str | None,
    source_hash: str,
) -> JdProfileData:
    extraction = await _parse_profile_chunks(client, model, job_description, job_title)
    return JdProfileData(
        **extraction.model_dump(),
        source=JdProfileSource(
            job_title=job_title,
            source_hash=source_hash,
            language=_detect_language(job_description),
        ),
    )


async def _parse_profile_chunks(
    client: SupportsStreamingMessages,
    model: str,
    job_description: str,
    job_title: str | None,
) -> JdProfileExtractionResult:
    """并发提取互相独立的 JD 语义块，再合并成统一 profile。"""
    chunk_specs = (
        ("role", JdProfileRoleResult, "角色定位、团队上下文、关键词和任职要求"),
        ("responsibilities", JdProfileResponsibilitiesResult, "工作职责和可交付结果"),
        (
            "signals",
            JdProfileSignalsResult,
            "评估标准、正向匹配信号、反向筛选信号和核心筛选标准",
        ),
        ("strategy", JdProfileStrategyResult, "简历突出策略、面试策略和 JD 歧义"),
    )
    semaphore = asyncio.Semaphore(PROFILE_CHUNK_CONCURRENCY)

    async def run_chunk(
        name: str, schema: type[StrictBaseModel], focus: str
    ) -> tuple[str, StrictBaseModel]:
        async with semaphore:
            result = await call_structured_json(
                client,
                model,
                _build_chunk_system_prompt(schema, focus),
                _build_chunk_user_prompt(job_description, job_title, focus),
                schema,
                max_retries=MAX_RETRIES,
                max_tokens=PROFILE_CHUNK_MAX_TOKENS,
                temperature=0.0,
                post_validator=_make_chunk_validator(name, job_description),
                invalid_response_prefix=f"JD Profile {name} chunk validation failed",
            )
            return name, result

    results = await asyncio.gather(
        *(run_chunk(name, schema, focus) for name, schema, focus in chunk_specs)
    )
    chunks = dict(results)
    role = chunks["role"]
    responsibilities = chunks["responsibilities"]
    signals = chunks["signals"]
    strategy = chunks["strategy"]
    extraction = JdProfileExtractionResult(
        role_profile=role.role_profile,
        requirements=role.requirements,
        responsibilities=responsibilities.responsibilities,
        evaluation_rubric=signals.evaluation_rubric,
        fit_signals=signals.fit_signals,
        anti_fit_signals=signals.anti_fit_signals,
        core_selection_criteria=signals.core_selection_criteria,
        resume_strategy=strategy.resume_strategy,
        interview_strategy=strategy.interview_strategy,
        ambiguities=strategy.ambiguities,
    )
    error = _validate_profile_completeness(extraction, job_description)
    if error is not None:
        raise ValueError(error)
    return extraction


def _build_chunk_system_prompt(schema: type[StrictBaseModel], focus: str) -> str:
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
    return f"""\
You are a senior recruiting analyst extracting one focused part of a job description.
Return ONLY one JSON object matching this schema:
<json_schema>
{schema_json}
</json_schema>

Focus only on: {focus}.
Do not invent company facts,
candidate facts, or requirements. Extract concrete items instead of returning empty arrays
when the JD contains a matching section. Convert explicit negative hiring signals into
positive abilities the candidate must demonstrate when the schema asks for core criteria.
"""


def _build_chunk_user_prompt(
    job_description: str, job_title: str | None, focus: str
) -> str:
    title = f"Target role: {job_title}\n\n" if job_title else ""
    return (
        f"{title}Extract the following JD dimension: {focus}.\n\n"
        f"<job_description>\n{job_description}\n</job_description>"
    )


def _make_chunk_validator(
    chunk_name: str, job_description: str
) -> Callable[[StrictBaseModel], str | None]:
    requirements = _get_profile_completeness_requirements(job_description)

    def validator(result: StrictBaseModel) -> str | None:
        if chunk_name == "responsibilities" and requirements["responsibilities"]:
            if len(result.responsibilities) < 2:
                return "Extract at least two responsibilities from the JD responsibilities section."
        if chunk_name == "signals":
            if requirements["anti_fit"] and not result.anti_fit_signals:
                return "Extract the explicit anti-fit signals from the JD."
            if requirements["selection"] and not result.core_selection_criteria:
                return "Extract the team's core selection criteria from the JD."
            if (
                requirements["product_evaluation"]
                and not result.evaluation_rubric
                and not result.fit_signals
            ):
                return (
                    "Extract product and user-impact evaluation criteria from the JD."
                )
        return None

    return validator


def _validate_profile_completeness(
    profile: JdProfileExtractionResult, job_description: str
) -> str | None:
    """阻止模型静默丢弃 JD 中明确出现的语义章节。"""
    requirements = _get_profile_completeness_requirements(job_description)
    if requirements["responsibilities"] and len(profile.responsibilities) < 2:
        return "Extract at least two responsibilities from the JD's responsibilities section."
    if requirements["anti_fit"] and not profile.anti_fit_signals:
        return "Extract the explicit anti-fit signals from the JD."
    if requirements["selection"] and not profile.core_selection_criteria:
        return "Extract the team's core selection criteria and convert negative signals into positive criteria."
    if (
        requirements["product_evaluation"]
        and not profile.evaluation_rubric
        and not profile.fit_signals
    ):
        return "Extract product and user-impact evaluation criteria from the JD."
    return None


def _get_profile_completeness_requirements(job_description: str) -> dict[str, bool]:
    """根据 JD 标题和正文判断需要校验哪些语义分块。"""
    headings = _extract_jd_headings(job_description)
    lowered = job_description.casefold()
    return {
        "responsibilities": _has_heading_alias(headings, "responsibilities"),
        "anti_fit": _has_heading_alias(headings, "anti_fit"),
        "selection": _has_heading_alias(headings, "selection"),
        "product_evaluation": any(
            marker.casefold() in lowered for marker in _PRODUCT_SIGNAL_MARKERS
        ),
    }


def _extract_jd_headings(job_description: str) -> set[str]:
    headings: set[str] = set()
    for line in job_description.splitlines():
        match = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", line)
        if match:
            heading = re.sub(r"[：:]+$", "", match.group(1))
            headings.add(_normalize_jd_heading(heading))
    return headings


def _has_heading_alias(headings: set[str], section: str) -> bool:
    aliases = _JD_SECTION_ALIASES[section]
    return any(
        _normalize_jd_heading(alias) in heading
        or heading in _normalize_jd_heading(alias)
        for heading in headings
        for alias in aliases
    )


def _normalize_jd_heading(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value.casefold())


async def ensure_jd_profile(
    db: AsyncSession,
    resume: Resume,
    *,
    trigger: str,
    background_tasks: BackgroundTasks | None = None,
    provider_override: ProviderRuntimeConfig | None = None,
    mode: Literal["background", "inline"] = "background",
    retry_failed: bool = False,
) -> JobDescriptionProfile | None:
    source = get_resume_jd_source(resume)
    if source is None:
        log.info("jd_profile.skip_no_jd resume_id=%s trigger=%s", resume.id, trigger)
        return None
    job_description, job_title, source_hash = source

    await _mark_obsolete_profiles(db, resume.id, source_hash)
    profile = await _get_profile_by_hash(db, resume.id, source_hash)
    provider = provider_override or await _get_active_provider_config(db)
    created = False

    if profile is None:
        profile = JobDescriptionProfile(
            resume_id=resume.id,
            source_hash=source_hash,
            schema_version=JD_PROFILE_SCHEMA_VERSION,
            status="pending_config",
            trigger=trigger,
        )
        db.add(profile)
        await db.flush()
        created = True
        log.info(
            "jd_profile.created resume_id=%s source_hash=%s trigger=%s",
            resume.id,
            source_hash,
            trigger,
        )

    if profile.status == "ready":
        log.info(
            "jd_profile.reuse_ready resume_id=%s source_hash=%s trigger=%s",
            resume.id,
            source_hash,
            trigger,
        )
        await db.commit()
        return profile
    if not created and profile.status in {"queued", "running"}:
        existing_work = await _find_running_parse_work(db, resume.id, source_hash)
        if existing_work is not None:
            log.info(
                "jd_profile.reuse_inflight resume_id=%s source_hash=%s task_id=%s status=%s trigger=%s",
                resume.id,
                source_hash,
                existing_work.id,
                existing_work.status,
                trigger,
            )
            await db.commit()
            return profile
        log.warning(
            "jd_profile.recover_stuck_inflight resume_id=%s source_hash=%s profile_status=%s trigger=%s",
            resume.id,
            source_hash,
            profile.status,
            trigger,
        )
        profile.status = "failed"
        profile.error_message = "JD parse task was not found; ready to reschedule"
        profile.updated_at = utc_now()
    if profile.status == "failed" and not retry_failed:
        log.info(
            "jd_profile.skip_failed resume_id=%s source_hash=%s trigger=%s",
            resume.id,
            source_hash,
            trigger,
        )
        await db.commit()
        return profile

    if provider is None:
        profile.status = "pending_config"
        profile.trigger = trigger
        profile.updated_at = utc_now()
        log.info(
            "jd_profile.pending_config resume_id=%s source_hash=%s trigger=%s",
            resume.id,
            source_hash,
            trigger,
        )
        await db.commit()
        return profile

    if mode == "inline" or background_tasks is None:
        log.info(
            "jd_profile.parse_inline resume_id=%s source_hash=%s trigger=%s model=%s",
            resume.id,
            source_hash,
            trigger,
            provider.model,
        )
        client = get_client(provider.provider_type, provider.api_key, provider.base_url)
        return await _parse_profile_into_record(
            db,
            profile,
            client,
            provider,
            job_description,
            job_title,
            source_hash,
            trigger,
            suppress_errors=True,
        )

    log.info(
        "jd_profile.queue resume_id=%s source_hash=%s trigger=%s model=%s",
        resume.id,
        source_hash,
        trigger,
        provider.model,
    )
    await _queue_profile_task(db, profile, provider, trigger, background_tasks)
    return profile


async def persist_profile_result(
    db: AsyncSession,
    *,
    resume_id: str,
    job_description: str,
    job_title: str | None,
    provider: ProviderRuntimeConfig,
    trigger: str,
    profile_data: JdProfileData | None,
    error_message: str | None,
) -> JobDescriptionProfile:
    source_hash = calculate_jd_source_hash(job_description, job_title)
    profile = await _get_profile_by_hash(db, resume_id, source_hash)
    if profile is None:
        profile = JobDescriptionProfile(
            resume_id=resume_id,
            source_hash=source_hash,
            schema_version=JD_PROFILE_SCHEMA_VERSION,
        )
        db.add(profile)

    profile.provider_type = provider.provider_type
    profile.model = provider.model
    profile.trigger = trigger
    profile.attempts = max(profile.attempts, 0) + 1
    profile.updated_at = utc_now()
    if profile_data is not None:
        profile.status = "ready"
        profile.profile_json = profile_data.model_dump_json()
        profile.error_message = None
    else:
        profile.status = "failed"
        profile.profile_json = "{}"
        profile.error_message = error_message or "JD profile parsing failed"
    return profile


async def get_current_profile_response(
    db: AsyncSession, resume: Resume
) -> CurrentJdProfileResponse:
    source = get_resume_jd_source(resume)
    if source is None:
        return CurrentJdProfileResponse(
            resume_id=resume.id,
            source_hash=None,
            has_job_description=False,
            profile=None,
            needs_parse=False,
        )

    _, _, source_hash = source
    profile = await _get_profile_by_hash(db, resume.id, source_hash)
    return CurrentJdProfileResponse(
        resume_id=resume.id,
        source_hash=source_hash,
        has_job_description=True,
        profile=(
            profile.to_pydantic().model_copy(update={"profile": None})
            if profile is not None
            else None
        ),
        needs_parse=profile is None or profile.status != "ready",
    )


async def wait_for_ready_profile(
    db: AsyncSession,
    resume: Resume,
    *,
    trigger: str,
    timeout: float = 120,
) -> JobDescriptionProfile:
    """Ensure the current sub-resume JD Profile is ready before generation."""
    source = get_resume_jd_source(resume)
    if source is None:
        raise ValueError("当前子简历缺少岗位描述")
    _, _, source_hash = source
    provider = await _get_active_provider_config(db)
    if provider is None:
        raise ValueError("请先在设置中配置 AI 提供商")

    await ensure_jd_profile(
        db,
        resume,
        trigger=trigger,
        provider_override=provider,
        mode="background",
        background_tasks=None,
        retry_failed=False,
    )
    elapsed = 0.0
    while elapsed < timeout:
        result = await db.execute(
            select(JobDescriptionProfile).where(
                JobDescriptionProfile.resume_id == resume.id,
                JobDescriptionProfile.source_hash == source_hash,
                JobDescriptionProfile.schema_version == JD_PROFILE_SCHEMA_VERSION,
            )
        )
        profile = result.scalar_one_or_none()
        if profile is not None:
            if profile.status == "ready":
                log.info(
                    "jd_profile.ready_for_generation resume_id=%s source_hash=%s trigger=%s profile_id=%s",
                    resume.id,
                    source_hash,
                    trigger,
                    profile.id,
                )
                return profile
            if profile.status in {"failed", "pending_config", "obsolete"}:
                raise ValueError(
                    profile.error_message or f"JD 解析状态为 {profile.status}"
                )
        await asyncio.sleep(1)
        db.expire_all()
        elapsed += 1
    raise TimeoutError("JD Profile 解析等待超时，请稍后查看任务通知")


async def queue_profiles_after_provider_update(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    trigger: str,
) -> None:
    provider = await _get_active_provider_config(db)
    if provider is None:
        return

    result = await db.execute(select(Resume).where(Resume.workspace_id.is_not(None)))
    resumes = result.scalars().all()
    for resume in resumes:
        if get_resume_jd_source(resume) is None:
            continue
        await ensure_jd_profile(
            db,
            resume,
            trigger=trigger,
            background_tasks=background_tasks,
            provider_override=provider,
            mode="background",
            retry_failed=True,
        )


async def run_jd_parse_task(
    db: AsyncSession,
    task_id: str,
    resume_id: str,
    source_hash: str,
    provider: ProviderRuntimeConfig,
    trigger: str,
) -> None:
    try:
        log.info(
            "jd_profile.task_start task_id=%s resume_id=%s source_hash=%s trigger=%s model=%s",
            task_id,
            resume_id,
            source_hash,
            trigger,
            provider.model,
        )
        await update_work_status(db, task_id, TaskStatus.RUNNING)
        await update_task_status(task_id, TaskStatus.RUNNING)

        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()
        if resume is None:
            raise ValueError(f"简历不存在: {resume_id}")

        current_source = get_resume_jd_source(resume)
        if current_source is None or current_source[2] != source_hash:
            await _mark_task_obsolete(db, task_id, resume_id, source_hash)
            return

        job_description, job_title, _ = current_source
        profile = await _get_profile_by_hash(db, resume_id, source_hash)
        if profile is None:
            profile = JobDescriptionProfile(
                resume_id=resume_id,
                source_hash=source_hash,
                schema_version=JD_PROFILE_SCHEMA_VERSION,
                status="running",
            )
            db.add(profile)
            await db.flush()

        client = get_client(provider.provider_type, provider.api_key, provider.base_url)
        parsed = await _parse_profile_into_record(
            db,
            profile,
            client,
            provider,
            job_description,
            job_title,
            source_hash,
            trigger,
            suppress_errors=False,
        )

        if parsed.status == "obsolete":
            await _mark_task_obsolete(db, task_id, resume_id, source_hash)
            return

        await update_work_status(db, task_id, TaskStatus.SUCCESS)
        await update_task_result(
            task_id,
            {
                "resume_id": resume_id,
                "source_hash": source_hash,
                "status": parsed.status,
            },
        )
        log.info(
            "jd_profile.task_success task_id=%s resume_id=%s source_hash=%s status=%s",
            task_id,
            resume_id,
            source_hash,
            parsed.status,
        )
        asyncio.create_task(cleanup_task(task_id, None))

    except Exception as exc:
        await db.rollback()
        log.exception("run_jd_parse_task error: %s", exc)
        await _mark_profile_failed(
            db, resume_id, source_hash, provider, trigger, str(exc)
        )
        await update_work_status(db, task_id, TaskStatus.ERROR)
        await update_task_error(task_id, f"run_jd_parse_task error: {exc}")
        asyncio.create_task(cleanup_task(task_id, None))
        raise


async def _parse_profile_into_record(
    db: AsyncSession,
    profile: JobDescriptionProfile,
    client: SupportsStreamingMessages,
    provider: ProviderRuntimeConfig,
    job_description: str,
    job_title: str | None,
    source_hash: str,
    trigger: str,
    *,
    suppress_errors: bool,
) -> JobDescriptionProfile:
    profile.status = "running"
    profile.provider_type = provider.provider_type
    profile.model = provider.model
    profile.trigger = trigger
    profile.attempts += 1
    profile.error_message = None
    profile.updated_at = utc_now()
    await db.commit()

    try:
        profile_data = await parse_jd_profile(
            client,
            provider.model,
            job_description,
            job_title,
            source_hash,
        )
    except Exception as exc:
        profile.status = "failed"
        profile.error_message = str(exc)
        profile.profile_json = "{}"
        profile.updated_at = utc_now()
        await db.commit()
        log.warning(
            "jd_profile.parse_failed resume_id=%s source_hash=%s trigger=%s error=%s",
            profile.resume_id,
            source_hash,
            trigger,
            exc,
        )
        if suppress_errors:
            return profile
        raise

    current_resume = await db.get(Resume, profile.resume_id)
    if current_resume is None:
        profile.status = "obsolete"
        await db.commit()
        return profile
    current_source = get_resume_jd_source(current_resume)
    if current_source is None or current_source[2] != source_hash:
        profile.status = "obsolete"
        profile.updated_at = utc_now()
        await db.commit()
        return profile

    profile.status = "ready"
    profile.profile_json = profile_data.model_dump_json()
    profile.error_message = None
    profile.updated_at = utc_now()
    await db.commit()
    await db.refresh(profile)
    log.info(
        "jd_profile.parse_ready resume_id=%s source_hash=%s trigger=%s requirements=%s",
        profile.resume_id,
        source_hash,
        trigger,
        len(profile_data.requirements),
    )
    return profile


async def _queue_profile_task(
    db: AsyncSession,
    profile: JobDescriptionProfile,
    provider: ProviderRuntimeConfig,
    trigger: str,
    background_tasks: BackgroundTasks | None,
) -> None:
    existing_work = await _find_running_parse_work(
        db, profile.resume_id, profile.source_hash
    )
    if existing_work is not None:
        profile.status = "queued" if existing_work.status == "pending" else "running"
        profile.provider_type = provider.provider_type
        profile.model = provider.model
        profile.trigger = trigger
        profile.updated_at = utc_now()
        await db.commit()
        log.info(
            "jd_profile.queue_reuse task_id=%s resume_id=%s source_hash=%s status=%s",
            existing_work.id,
            profile.resume_id,
            profile.source_hash,
            existing_work.status,
        )
        return

    task_id = str(uuid.uuid4())
    work = build_work_record(
        task_id,
        TaskType.JD_PARSE,
        {
            "resume_id": profile.resume_id,
            "source_hash": profile.source_hash,
            "schema_version": JD_PROFILE_SCHEMA_VERSION,
            "trigger": trigger,
        },
    )
    db.add(work)
    profile.status = "queued"
    profile.provider_type = provider.provider_type
    profile.model = provider.model
    profile.trigger = trigger
    profile.error_message = None
    profile.updated_at = utc_now()
    await db.commit()

    create_task(task_id, TaskType.JD_PARSE)
    if background_tasks is not None:
        background_tasks.add_task(
            run_jd_parse_task,
            db,
            task_id,
            profile.resume_id,
            profile.source_hash,
            provider,
            trigger,
        )
    log.info(
        "jd_profile.task_queued task_id=%s resume_id=%s source_hash=%s trigger=%s",
        task_id,
        profile.resume_id,
        profile.source_hash,
        trigger,
    )


async def _get_active_provider_config(
    db: AsyncSession,
) -> ProviderRuntimeConfig | None:
    result = await db.execute(
        select(UserConfig).where(UserConfig.key == PROVIDER_CONFIG_KEY)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    config = ProviderConfig.model_validate(row.value)
    if config.active not in {"openai", "anthropic"}:
        return None
    provider = config.providers.get(config.active)
    if (
        provider is None
        or not provider.api_key.strip()
        or not provider.base_url.strip()
        or not provider.model.strip()
    ):
        return None
    return ProviderRuntimeConfig(
        provider_type=config.active,
        api_key=provider.api_key,
        base_url=provider.base_url,
        model=provider.model,
    )


async def _get_profile_by_hash(
    db: AsyncSession,
    resume_id: str,
    source_hash: str,
) -> JobDescriptionProfile | None:
    result = await db.execute(
        select(JobDescriptionProfile).where(
            JobDescriptionProfile.resume_id == resume_id,
            JobDescriptionProfile.source_hash == source_hash,
            JobDescriptionProfile.schema_version == JD_PROFILE_SCHEMA_VERSION,
        )
    )
    return result.scalar_one_or_none()


async def _mark_obsolete_profiles(
    db: AsyncSession,
    resume_id: str,
    current_source_hash: str,
) -> None:
    result = await db.execute(
        select(JobDescriptionProfile).where(
            JobDescriptionProfile.resume_id == resume_id,
            JobDescriptionProfile.source_hash != current_source_hash,
            JobDescriptionProfile.status != "obsolete",
        )
    )
    profiles = result.scalars().all()
    for profile in profiles:
        profile.status = "obsolete"
        profile.updated_at = utc_now()


async def _find_running_parse_work(
    db: AsyncSession,
    resume_id: str,
    source_hash: str,
) -> BaseWork | None:
    result = await db.execute(
        select(BaseWork).where(
            BaseWork.task_type == TaskType.JD_PARSE.value,
            BaseWork.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value]),
            BaseWork.meta_info["resume_id"].as_string() == resume_id,
            BaseWork.meta_info["source_hash"].as_string() == source_hash,
        )
    )
    return result.scalar_one_or_none()


async def _mark_profile_failed(
    db: AsyncSession,
    resume_id: str,
    source_hash: str,
    provider: ProviderRuntimeConfig,
    trigger: str,
    error_message: str,
) -> None:
    profile = await _get_profile_by_hash(db, resume_id, source_hash)
    if profile is None:
        profile = JobDescriptionProfile(
            resume_id=resume_id,
            source_hash=source_hash,
            schema_version=JD_PROFILE_SCHEMA_VERSION,
        )
        db.add(profile)
    profile.status = "failed"
    profile.provider_type = provider.provider_type
    profile.model = provider.model
    profile.trigger = trigger
    profile.error_message = error_message
    profile.updated_at = utc_now()
    await db.commit()


async def _mark_task_obsolete(
    db: AsyncSession,
    task_id: str,
    resume_id: str,
    source_hash: str,
) -> None:
    profile = await _get_profile_by_hash(db, resume_id, source_hash)
    if profile is not None:
        profile.status = "obsolete"
        profile.updated_at = utc_now()
        await db.commit()
    await update_work_status(db, task_id, TaskStatus.SUCCESS)
    await update_task_result(
        task_id,
        {
            "resume_id": resume_id,
            "source_hash": source_hash,
            "status": "obsolete",
        },
    )
    asyncio.create_task(cleanup_task(task_id, None))


def _detect_language(text: str) -> str:
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    ascii_letters = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    if cjk > ascii_letters / 4:
        return "zh"
    if ascii_letters:
        return "en"
    return "unknown"
