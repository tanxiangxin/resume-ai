import json
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.greeting.service import create_greeting_task, list_greeting_batches
from chiren_backend.platform.db import get_session
from chiren_backend.platform.models import GreetingGenerationBatch, Resume
from shared.types.greeting import GreetingBatchSchema
from shared.types.work import TaskIdResponse

router = APIRouter(prefix="/greeting", tags=["greeting"])


class GreetingBatchUpdate(BaseModel):
    user_edits: dict[str, str] | None = Field(default=None)
    selected_style: str | None = Field(default=None)


@router.post("/generate", summary="生成 Boss 招呼语")
async def generate_greeting(
    background_tasks: BackgroundTasks,
    resume_id: Annotated[str, Body(embed=True)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskIdResponse:
    resume = await db.get(Resume, resume_id)
    if resume is None or resume.workspace_id is None:
        raise HTTPException(status_code=404, detail="子简历不存在")
    try:
        task_id, _ = await create_greeting_task(db, resume, background_tasks)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return TaskIdResponse(task_id=task_id)


@router.get("/{resume_id}/list")
async def get_greeting_batches(
    resume_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[GreetingBatchSchema]:
    return await list_greeting_batches(db, resume_id)


@router.get("/batch/{batch_id}")
async def get_greeting_batch(
    batch_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> GreetingBatchSchema:
    batch = await db.get(GreetingGenerationBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="招呼语生成批次不存在")
    return batch.to_pydantic()


@router.patch("/batch/{batch_id}")
async def update_greeting_batch(
    batch_id: str,
    payload: Annotated[GreetingBatchUpdate, Body()],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> GreetingBatchSchema:
    batch = await db.get(GreetingGenerationBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="招呼语生成批次不存在")
    if payload.user_edits is not None:
        batch.user_edits_json = json.dumps(payload.user_edits, ensure_ascii=False)
    if payload.selected_style is not None:
        batch.selected_style = payload.selected_style
    await db.commit()
    await db.refresh(batch)
    return batch.to_pydantic()
