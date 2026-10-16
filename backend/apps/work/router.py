import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from apps.work.sse import sse_event_generator
from chiren_backend.platform.db import get_session
from chiren_backend.platform.models import BaseWork
from chiren_backend.platform.task_state import tasks
from shared.types.work import WorkSchema

router = APIRouter(prefix="/work", tags=["work"])


@router.get("/list", summary="查询任务列表")
async def get_work_list(
    db: Annotated[AsyncSession, Depends(get_session)],
    task_type: Annotated[str | None, Query(description="任务类型")] = None,
    status: Annotated[str | None, Query(description="任务状态")] = None,
    meta_contains: Annotated[
        str | None, Query(description='meta_info包含的JSON，如{"resume_id":"xxx"}')
    ] = None,
) -> list[WorkSchema]:
    query = select(BaseWork)
    if task_type:
        query = query.where(BaseWork.task_type == task_type)
    if status:
        query = query.where(BaseWork.status == status)
    if meta_contains:
        try:
            filter_dict = json.loads(meta_contains)
            if not isinstance(filter_dict, dict):
                raise HTTPException(
                    status_code=400, detail="meta_contains必须是JSON对象"
                )
            json_filters = [
                BaseWork.meta_info[k].as_string() == str(v)
                for k, v in filter_dict.items()
            ]
            query = query.where(and_(*json_filters))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="meta_contains必须是有效JSON")
    result = await db.execute(query)
    work_list = result.scalars().all()
    return [WorkSchema.model_validate(item) for item in work_list]


@router.get("/{id}", summary="按id查询单个任务")
async def get_by_id(
    id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> WorkSchema:
    result = await db.execute(select(BaseWork).where(BaseWork.id == id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="没有该任务")
    return WorkSchema.model_validate(item)


@router.delete("/delete/{id}", summary="根据id删除任务")
async def delete_by_id(
    id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> WorkSchema:
    result = await db.execute(select(BaseWork).where(BaseWork.id == id))
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(status_code=404, detail="没有该任务")
    try:
        await db.delete(work)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="删除失败")
    return WorkSchema.model_validate(work)


@router.get("/stream/{task_id}", summary="通过SSE流式获取任务结果")
async def stream_task_result(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return EventSourceResponse(sse_event_generator(task_id))
