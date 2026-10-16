from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.jd_profile.service import (
    ensure_jd_profile,
    get_current_profile_response,
)
from chiren_backend.platform.db import get_session
from chiren_backend.platform.models import Resume
from shared.types.jd_profile import CurrentJdProfileResponse

router = APIRouter(prefix="/jd-profile", tags=["jd-profile"])


@router.get("/{resume_id}/current", summary="获取当前 JD Profile 状态")
async def get_current_profile(
    resume_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentJdProfileResponse:
    resume = await _load_resume(db, resume_id)
    return await get_current_profile_response(db, resume)


@router.post("/{resume_id}/retry", summary="重试当前 JD Profile 解析")
async def retry_current_profile(
    resume_id: str,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentJdProfileResponse:
    resume = await _load_resume(db, resume_id)
    await ensure_jd_profile(
        db,
        resume,
        trigger="manual_retry",
        background_tasks=background_tasks,
        mode="background",
        retry_failed=True,
    )
    return await get_current_profile_response(db, resume)


async def _load_resume(db: AsyncSession, resume_id: str) -> Resume:
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"简历不存在: {resume_id}",
        )
    return resume
