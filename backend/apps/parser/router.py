"""Parser 路由定义。"""

import uuid
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.parser.service import infer_parser_type, retry_parser_task, run_parser_task
from chiren_backend.platform.db import get_session
from chiren_backend.platform.llm import get_client
from chiren_backend.platform.models import BaseWork
from chiren_backend.platform.task_state import create_task, tasks
from chiren_backend.platform.work_records import build_work_record
from shared.types.task import TaskStatus, TaskType
from shared.types.work import TaskIdResponse

router = APIRouter(prefix="/parser", tags=["parser"])


@router.post(
    "",
    summary="上传文档并启动解析任务",
    responses={
        400: {"description": "不支持的文件类型或文件超过10MB"},
    },
)
async def parse_document(
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile, File(description="要解析的文件，最大 10MB")],
    type: Annotated[
        Literal["openai", "anthropic"],
        Form(description="LLM 供应商类型", examples=["openai"]),
    ],
    base_url: Annotated[
        str, Form(description="AI API 地址", examples=["http://127.0.0.1:5564/openai"])
    ],
    api_key: Annotated[str, Form(description="AI API 密钥", examples=["sk-xxx"])],
    model: Annotated[str, Form(description="模型名称", examples=["gpt-4o"])],
    template: Annotated[str, Form(description="模板名称", examples=["classic"])],
    title: Annotated[
        str, Form(description="简历标题", examples=["未命名简历"])
    ] = "未命名简历",
) -> TaskIdResponse:
    try:
        infer_parser_type(file.filename, file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_id = str(uuid.uuid4())
    create_task(task_id, TaskType.PARSE)

    from apps.parser.storage import save_upload_file

    file_path, original_name = await save_upload_file(file, task_id)

    # 创建任务记录到数据库
    work = build_work_record(
        task_id,
        TaskType.PARSE,
        meta_info={
            "file_name": original_name,
            "src": file_path,
            "template": template,
            "title": title,
        },
    )
    db.add(work)
    await db.commit()

    client = get_client(type, api_key, base_url)
    background_tasks.add_task(
        run_parser_task, db, task_id, file_path, client, model, template, title
    )

    return TaskIdResponse(task_id=task_id)


@router.post(
    "/retry/{task_id}",
    summary="重试失败的任务",
    responses={
        404: {"description": "任务不存在"},
        400: {"description": "任务状态不是错误，无法重试"},
    },
)
async def retry_failed_task(
    background_tasks: BackgroundTasks,
    task_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
    type: Annotated[
        Literal["openai", "anthropic"],
        Form(description="LLM 供应商类型", examples=["openai"]),
    ],
    base_url: Annotated[
        str, Form(description="AI API 地址", examples=["http://127.0.0.1:5564/openai"])
    ],
    api_key: Annotated[str, Form(description="AI API 密钥", examples=["sk-xxx"])],
    model: Annotated[str, Form(description="模型名称", examples=["gpt-4o"])],
) -> TaskIdResponse:
    if task_id in tasks:
        return TaskIdResponse(task_id=task_id)

    # 从数据库查询任务
    result = await db.execute(select(BaseWork).where(BaseWork.id == task_id))
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(status_code=404, detail="任务不存在")

    if work.status != TaskStatus.ERROR.value:
        raise HTTPException(status_code=400, detail="只有错误状态的任务才能重试")

    meta_info = work.meta_info or {}
    file_path = meta_info.get("src", "")
    template = meta_info.get("template", "classic")
    title = meta_info.get("title", "未命名简历")

    create_task(task_id, TaskType.PARSE)

    client = get_client(type, api_key, base_url)

    background_tasks.add_task(
        retry_parser_task,
        db,
        task_id,
        file_path,
        client,
        model,
        template,
        title,
    )

    return TaskIdResponse(task_id=task_id)
