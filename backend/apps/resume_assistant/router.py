import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette import EventSourceResponse

from apps.resume_assistant.agent_service import resume_assistant_service
from apps.resume_assistant.schemas import ResumeAssistantRequest, SubResumeCreateRequest
from apps.resume_assistant.task_service import run_sub_resume_task
from chiren_backend.platform.db import get_session
from chiren_backend.platform.llm import get_client
from chiren_backend.platform.models import Resume, ResumeSection
from chiren_backend.platform.task_state import create_task
from chiren_backend.platform.work_records import build_work_record
from shared.types.task import TaskType
from shared.types.work import TaskIdResponse

router = APIRouter(prefix="/resume-assistant", tags=["resume-assistant"])


@router.post(
    "",
    summary="AI 简历助手 Agent",
)
async def resume_assistant(
    request: Annotated[ResumeAssistantRequest, Body(description="AI 简历助手请求参数")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EventSourceResponse:
    """AI 简历助手 Agent 接口。

    基于 LLM 的 Agent 接口，LLM 作为大脑，通过工具操作简历数据。
    自动处理多轮工具调用，并将 AI 回复和工具调用记录自动写入数据库。

    注意：调用此接口前，**用户消息需自行入库**。

    请求参数：
        - **resume_id**: 简历唯一标识
        - **type**: LLM 供应商类型（openai / anthropic）
        - **base_url**: AI API 地址
        - **api_key**: AI API 密钥
        - **model**: 模型名称
        - **input**: 用户输入/指令

    SSE 事件类型：

    + **next**: 开始新一轮交互。当 AI 需要多轮调用工具时会发送此事件。
    + **thinking_start**: AI 开始深度思考（CoT）。首次收到思考内容前发送。
    + **thinking_delta**: AI 思考内容的增量。payload: ``{"text": "思考内容片段"}``。
    + **text_start**: AI 开始输出文本回复。首次收到文本内容前发送。
    + **text_delta**: AI 输出文本的增量。payload: ``{"text": "文本内容片段"}``。
    + **tool_use**: AI 调用工具。payload: ``{"name": "工具名", "id": "调用ID", "input": {参数}}``。
    + **tool_result**: 工具执行结果。payload: ``{"is_error": bool, "tool_use_id": "调用ID", "content": "结果内容"}``。
    + **done**: 会话正常结束。
    + **error**: 发生错误。payload: ``{"message": "错误信息"}``。
    """
    sections_result = await db.execute(
        select(ResumeSection)
        .where(
            ResumeSection.resume_id == request.resume_id, ResumeSection.visible == True
        )
        .order_by(ResumeSection.sort_order.asc())
    )
    resume_section_list = sections_result.scalars().all()

    sections = [resume.to_pydantic() for resume in resume_section_list]

    resume_result = await db.execute(
        select(Resume).where(Resume.id == request.resume_id)
    )
    resume = resume_result.scalar_one_or_none()

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"简历不存在: {request.resume_id}",
        )

    return await resume_assistant_service(request, resume, sections, db)


@router.post(
    "/sub-resumes",
    summary="根据 JD 创建子简历",
)
async def create_sub_resume(
    background_tasks: BackgroundTasks,
    request: Annotated[SubResumeCreateRequest, Body(description="子简历创建请求参数")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskIdResponse:

    section_result = await db.execute(
        select(Resume).where(Resume.id == request.workspace_id)
    )
    resume = section_result.scalar_one_or_none()

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"简历不存在: {request.workspace_id}",
        )

    task_id = str(uuid.uuid4())

    section_result = await db.execute(
        select(ResumeSection)
        .where(ResumeSection.resume_id == request.workspace_id)
        .order_by(ResumeSection.sort_order.asc())
    )

    resume_section_list = section_result.scalars().all()
    sections = [resume.to_pydantic() for resume in resume_section_list]

    # 创建任务记录到数据库
    work = build_work_record(
        task_id,
        TaskType.SUB_RESUME_GENERATE,
        meta_info={
            "job_description": request.job_description,
            "job_title": request.job_title,
            "template": request.template,
            "title": request.title,
        },
    )
    db.add(work)
    await db.commit()

    create_task(task_id, TaskType.SUB_RESUME_GENERATE)

    client = get_client(request.type, request.api_key, request.base_url)

    background_tasks.add_task(
        run_sub_resume_task,
        db,
        task_id,
        client,
        request,
        sections,
    )

    return TaskIdResponse(task_id=task_id)
