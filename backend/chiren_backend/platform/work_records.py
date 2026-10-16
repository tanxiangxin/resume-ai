"""持久化 work 任务记录辅助函数。"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chiren_backend.platform.models import SHANGHAI_TZ, BaseWork
from shared.types.task import TaskStatus, TaskType


def build_work_record(
    task_id: str,
    task_type: TaskType,
    meta_info: dict[str, Any] | None = None,
    status: TaskStatus = TaskStatus.PENDING,
) -> BaseWork:
    """构建 BaseWork 行，但不加入数据库会话。"""
    return BaseWork(
        id=task_id,
        task_type=task_type.value,
        status=status.value,
        meta_info=meta_info or {},
    )


async def update_work_status(
    db: AsyncSession,
    task_id: str,
    status: TaskStatus,
    error: str | None = None,
    *,
    commit: bool = True,
) -> BaseWork | None:
    """更新持久化 work 记录状态。"""
    result = await db.execute(select(BaseWork).where(BaseWork.id == task_id))
    work = result.scalar_one_or_none()
    if work:
        work.status = status.value
        work.updated_at = datetime.now(SHANGHAI_TZ)
        if error:
            work.error_message = error
        if commit:
            await db.commit()
    return work


async def update_work_status_in_new_session(
    task_id: str,
    status: TaskStatus,
    error: str | None = None,
) -> BaseWork | None:
    """在独立数据库会话里更新持久化 work 状态。"""
    from chiren_backend.platform.db import async_session

    async with async_session() as session:
        return await update_work_status(session, task_id, status, error)


async def find_work_by_meta(
    db: AsyncSession,
    task_type: TaskType,
    meta_key: str,
    meta_value: str,
    statuses: tuple[TaskStatus, ...] = (TaskStatus.RUNNING, TaskStatus.PENDING),
) -> BaseWork | None:
    """按任务类型、状态和 JSON 元数据查询已有 work 记录。"""
    result = await db.execute(
        select(BaseWork).where(
            BaseWork.task_type == task_type.value,
            BaseWork.status.in_([status.value for status in statuses]),
            BaseWork.meta_info[meta_key].as_string() == meta_value,
        )
    )
    return result.scalar_one_or_none()
