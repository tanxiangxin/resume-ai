import json
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.jd_profile.service import ensure_jd_profile
from apps.resume.schemas import (
    CreateSubResumeRequest,
    CreateWorkspaceRequest,
)
from apps.resume.service import copy_sections_from_workspace, create_default_sections
from chiren_backend.platform.db import get_session
from chiren_backend.platform.models import (
    ConversationMessageRecord,
    InterviewCollection,
    Resume,
)
from shared.types.resume import ResumeSchema

router = APIRouter(prefix="/resume", tags=["resume"])


class SubResumeInfo(ResumeSchema):
    """子简历简要信息"""

    model_config = ResumeSchema.model_config


class WorkspaceSummary(ResumeSchema):
    """工作空间概要，含子简历 id 列表"""

    model_config = ResumeSchema.model_config

    sub_resume_ids: list[str] = Field(
        default_factory=list, description="子简历 id 列表"
    )


class WorkspaceDetail(WorkspaceSummary):
    """工作空间详情，包含完整子简历列表"""

    sub_resumes: list[SubResumeInfo] = Field(
        default_factory=list, description="子简历列表"
    )


@router.get("/list", summary="查询workspace_id = null的主简历")
async def list_resumes(
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[WorkspaceSummary]:
    result = await db.execute(
        select(Resume)
        .where(Resume.workspace_id.is_(None))
        .options(selectinload(Resume.versions))
    )
    resume_list = result.scalars().all()

    return [
        WorkspaceSummary(
            **resume.to_pydantic().model_dump(),
            sub_resume_ids=[v.id for v in resume.versions],
        )
        for resume in resume_list
    ]


@router.get("/{id}", summary="根据简历id查询单份简历详情")
async def get_resume(
    id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> WorkspaceDetail:
    result = await db.execute(
        select(Resume).where(Resume.id == id).options(selectinload(Resume.versions))
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    return WorkspaceDetail(
        **resume.to_pydantic().model_dump(),
        sub_resume_ids=[v.id for v in resume.versions],
        sub_resumes=[
            SubResumeInfo(**v.to_pydantic().model_dump()) for v in resume.versions
        ],
    )


@router.post("/create", summary="新建 Workspace（主简历）")
async def create_workspace(
    data: CreateWorkspaceRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> WorkspaceSummary:
    resume_id = str(uuid.uuid4())

    resume = Resume(
        id=resume_id,
        workspace_id=None,
        title=data.title,
        template=data.template,
        theme_config=json.dumps(data.theme_config, ensure_ascii=False),
        language=data.language,
    )
    db.add(resume)

    await create_default_sections(resume_id, db)

    try:
        await db.commit()
        await db.refresh(resume)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="新增失败")

    return WorkspaceSummary(**resume.to_pydantic().model_dump(), sub_resume_ids=[])


@router.post("/sub/create", summary="新建子简历")
async def create_sub_resume(
    data: CreateSubResumeRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> WorkspaceSummary:
    result = await db.execute(
        select(Resume).where(
            Resume.id == data.workspace_id, Resume.workspace_id.is_(None)
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="所属 Workspace 不存在")

    resume_id = str(uuid.uuid4())

    meta_info = {"job_description": data.job_description}

    if data.job_title:
        meta_info["job_title"] = data.job_title

    resume = Resume(
        id=resume_id,
        workspace_id=data.workspace_id,
        title=data.title,
        template=data.template,
        theme_config=json.dumps(data.theme_config, ensure_ascii=False),
        language=data.language,
        meta_info=meta_info,
    )

    db.add(resume)

    await copy_sections_from_workspace(workspace.id, resume_id, db)

    try:
        await db.commit()
        await db.refresh(resume)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="新增失败")

    await ensure_jd_profile(
        db,
        resume,
        trigger="direct_create",
        background_tasks=background_tasks,
        mode="background",
        retry_failed=False,
    )

    return WorkspaceSummary(**resume.to_pydantic().model_dump(), sub_resume_ids=[])


@router.put("/update", summary="修改简历")
async def update_resume(
    data: ResumeSchema,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ResumeSchema:
    result = await db.execute(select(Resume).where(Resume.id == data.id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "theme_config":
            value = json.dumps(value, ensure_ascii=False)
        setattr(resume, key, value)

    try:
        await db.commit()
        await db.refresh(resume)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="修改失败")

    if resume.workspace_id is not None and resume.meta_info:
        await ensure_jd_profile(
            db,
            resume,
            trigger="jd_update",
            background_tasks=background_tasks,
            mode="background",
            retry_failed=False,
        )
    return resume.to_pydantic()


@router.delete("/delete", summary="根据简历id删除简历")
async def delete_resume(
    id: Annotated[str, Query(description="简历ID")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    from apps.resume_assistant.conversation_store import ConversationStore

    result = await db.execute(
        select(Resume).where(Resume.id == id).options(selectinload(Resume.versions))
    )
    parent = result.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="简历不存在")

    all_resume_ids = [parent.id] + [v.id for v in parent.versions]

    collections_result = await db.execute(
        select(InterviewCollection)
        .where(InterviewCollection.sub_resume_id.in_(all_resume_ids))
        .options(selectinload(InterviewCollection.rounds))
    )
    interview_collections = collections_result.scalars().all()
    interview_round_ids = [r.id for c in interview_collections for r in c.rounds]

    all_conversation_ids = all_resume_ids + interview_round_ids
    if all_conversation_ids:
        await db.execute(
            delete(ConversationMessageRecord).where(
                ConversationMessageRecord.conversation_id.in_(all_conversation_ids)
            )
        )

    await db.delete(parent)

    try:
        await db.commit()
        conversation_store = ConversationStore()
        for resume_id in all_resume_ids:
            conversation_store.delete(resume_id)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="删除失败")
    return None
