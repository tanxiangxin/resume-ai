import asyncio
import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.jd_analysis.call_llm import executor_llm
from apps.jd_profile.service import ProviderRuntimeConfig, ensure_jd_profile
from chiren_backend.platform.llm import SupportsStreamingMessages
from chiren_backend.platform.models import JobDescriptionAnalysis, Resume, ResumeSection
from chiren_backend.platform.task_state import (
    cleanup_task,
    update_task_error,
    update_task_result,
    update_task_status,
)
from chiren_backend.platform.work_records import update_work_status
from shared.types.task import TaskStatus

log = logging.getLogger(__name__)


async def run_match_task(
    db: AsyncSession,
    task_id: str,
    client: SupportsStreamingMessages,
    model: str,
    provider_config: ProviderRuntimeConfig,
    resume_id: str,
    job_description: str,
    job_title: str | None = None,
) -> None:

    try:
        # 查询现有的 section 信息
        sections_result = await db.execute(
            select(ResumeSection)
            .where(ResumeSection.resume_id == resume_id, ResumeSection.visible == True)
            .order_by(ResumeSection.sort_order)
        )

        resume_section_list = sections_result.scalars().all()

        sections = [resume.to_pydantic() for resume in resume_section_list]

        await update_work_status(db, task_id, TaskStatus.RUNNING)
        await update_task_status(task_id, TaskStatus.RUNNING)

        resume_result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = resume_result.scalar_one_or_none()
        jd_profile = None
        if resume is not None:
            profile_record = await ensure_jd_profile(
                db,
                resume,
                trigger="jd_score",
                provider_override=provider_config,
                mode="inline",
                retry_failed=True,
            )
            if profile_record is not None and profile_record.status == "ready":
                jd_profile = profile_record.to_pydantic().profile

        match_result, extraction = await executor_llm(
            client, model, sections, job_description, job_title, jd_profile
        )

        job_description_analysis = JobDescriptionAnalysis(
            resume_id=resume_id,
            job_description=job_description,
            summary=match_result.summary,
            overall_score=match_result.overall_score,
            ats_score=match_result.ats_score,
            keyword_matches=json.dumps(
                [k.model_dump() for k in match_result.keyword_matches],
                ensure_ascii=False,
            ),
            missing_keywords=json.dumps(
                [k.model_dump() for k in match_result.missing_keywords],
                ensure_ascii=False,
            ),
            suggestions=json.dumps(
                [s.model_dump() for s in match_result.suggestions],
                ensure_ascii=False,
            ),
            partial_matches=json.dumps(
                [p.model_dump() for p in match_result.partial_matches],
                ensure_ascii=False,
            ),
            skill_matches=json.dumps(
                [s.model_dump() for s in match_result.skill_matches],
                ensure_ascii=False,
            ),
            strengths=json.dumps(
                [st.model_dump() for st in match_result.strengths],
                ensure_ascii=False,
            ),
            jd_requirements=json.dumps(
                [r.model_dump() for r in extraction.requirements],
                ensure_ascii=False,
            ),
        )
        db.add(job_description_analysis)
        await db.commit()
        await db.refresh(job_description_analysis)

        await update_work_status(db, task_id, TaskStatus.SUCCESS)
        await update_task_result(
            task_id,
            {
                "jd_analysis_id": job_description_analysis.id,
            },
        )

        asyncio.create_task(cleanup_task(task_id, None))

    except Exception as e:
        await db.rollback()
        log.error(f"run_match_task error: {str(e)}")
        await update_work_status(db, task_id, TaskStatus.ERROR)
        await update_task_error(task_id, f"run_match_task error: {str(e)}")
        asyncio.create_task(cleanup_task(task_id, None))
        raise
