from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.cover_letter.schemas import CoverLetterRequest
from apps.cover_letter.service import (
    create_cover_letter_task,
    list_cover_letter_batches,
    update_cover_letter_batch,
)
from chiren_backend.platform.db import get_session
from chiren_backend.platform.models import CoverLetterGenerationBatch, Resume
from shared.types.cover_letter import (
    CoverLetterBatchSchema,
    CoverLetterGenerationParams,
)
from shared.types.work import TaskIdResponse

router = APIRouter(prefix="/cover-letter", tags=["cover-letter"])


@router.post("", summary="创建求职信生成任务")
async def generate_cover_letter(
    background_tasks: BackgroundTasks,
    request: Annotated[CoverLetterRequest, Body(description="求职信生成参数")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskIdResponse:
    resume = await db.get(Resume, request.resume_id)
    if resume is None or resume.workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="子简历不存在"
        )
    try:
        task_id, _ = await create_cover_letter_task(
            db,
            resume,
            CoverLetterGenerationParams.model_validate(
                request.model_dump(exclude={"resume_id"})
            ),
            background_tasks,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return TaskIdResponse(task_id=task_id)


@router.get("/{resume_id}/list")
async def get_cover_letter_batches(
    resume_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[CoverLetterBatchSchema]:
    try:
        return await list_cover_letter_batches(db, resume_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/batch/{batch_id}")
async def get_cover_letter_batch(
    batch_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CoverLetterBatchSchema:
    batch = await db.get(CoverLetterGenerationBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="求职信生成批次不存在")
    resume = await db.get(Resume, batch.resume_id)
    if resume is None or resume.workspace_id is None:
        raise HTTPException(status_code=404, detail="子简历不存在")
    return batch.to_pydantic()


@router.patch("/batch/{batch_id}")
async def edit_cover_letter_batch(
    batch_id: str,
    content: Annotated[str, Body(embed=True, min_length=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CoverLetterBatchSchema:
    try:
        batch = await db.get(CoverLetterGenerationBatch, batch_id)
        if batch is None:
            raise ValueError("求职信生成批次不存在")
        resume = await db.get(Resume, batch.resume_id)
        if resume is None or resume.workspace_id is None:
            raise ValueError("子简历不存在")
        return await update_cover_letter_batch(db, batch_id, content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
