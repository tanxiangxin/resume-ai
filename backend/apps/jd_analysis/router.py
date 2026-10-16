import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.jd_analysis.schemas import MatchRequest
from apps.jd_analysis.service import run_match_task
from apps.jd_profile.service import ProviderRuntimeConfig
from chiren_backend.platform.db import get_session
from chiren_backend.platform.llm import get_client
from chiren_backend.platform.models import JobDescriptionAnalysis, Resume
from chiren_backend.platform.task_state import create_task
from chiren_backend.platform.work_records import build_work_record, find_work_by_meta
from shared.types.jd_analysis import JobDescriptionAnalysisSchema
from shared.types.task import TaskStatus, TaskType
from shared.types.work import TaskIdResponse

router = APIRouter(
    prefix="/jd-analysis",
    tags=["jd-analysis"],
)


@router.get("/list/{resume_id}", summary="获取简历的职位分析列表(按时间降序)")
async def list_jd_analysis(
    resume_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[JobDescriptionAnalysisSchema]:

    result = await db.execute(
        select(JobDescriptionAnalysis)
        .where(JobDescriptionAnalysis.resume_id == resume_id)
        .order_by(JobDescriptionAnalysis.created_at.desc())
    )

    jd_analysis_list = result.scalars().all()

    return [jd_analysis.to_pydantic() for jd_analysis in jd_analysis_list]


@router.get("/{jd_analysis_id}", summary="获取职位分析详情")
async def get_jd_analysis(
    jd_analysis_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> JobDescriptionAnalysisSchema:

    result = await db.execute(
        select(JobDescriptionAnalysis).where(
            JobDescriptionAnalysis.id == jd_analysis_id
        )
    )

    jd_analysis = result.scalars().first()

    return jd_analysis.to_pydantic()


@router.post("/match", summary="创建JD匹配评分任务")
async def create_score_task(
    background_tasks: BackgroundTasks,
    data: Annotated[MatchRequest, Body(description="jd评分请求参数")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskIdResponse:
    """创建JD匹配评分的后台任务.

    根据简历ID获取简历信息,提取其中的job_description和job_title,
    然后在后台启动LLM评分任务,返回任务ID供后续查询结果.
    """
    result = await db.execute(select(Resume).where(Resume.id == data.resume_id))
    resume = result.scalar_one_or_none()

    if resume is None:
        # 抛出404错误
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"简历不存在: {data.resume_id}",
        )

    if resume.meta_info is None or "job_description" not in resume.meta_info:
        # 抛出错误, 因为评分是针对有jd描述的简历的
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="简历缺少职位描述(job_description),无法进行评分",
        )

    # 检查是否存在正在进行的相同任务,返回已有的task_id
    existing_task = await find_work_by_meta(
        db,
        TaskType.JD_SCORE,
        "resume_id",
        data.resume_id,
        statuses=(TaskStatus.RUNNING,),
    )
    if existing_task is not None:
        return TaskIdResponse(task_id=existing_task.id)

    meta_info = resume.meta_info

    job_description: str = meta_info.get("job_description")

    job_title: str | None = meta_info.get("job_title")

    task_id = str(uuid.uuid4())

    work = build_work_record(
        task_id,
        TaskType.JD_SCORE,
        {
            "resume_id": resume.id,
            "workspace_id": resume.workspace_id,
            "title": resume.title,
        },
    )
    db.add(work)
    await db.commit()

    client = get_client(data.type, data.api_key, data.base_url)
    provider_config = ProviderRuntimeConfig(
        provider_type=data.type,
        api_key=data.api_key,
        base_url=data.base_url,
        model=data.model,
    )

    create_task(task_id, TaskType.JD_SCORE)

    background_tasks.add_task(
        run_match_task,
        db,
        task_id,
        client,
        data.model,
        provider_config,
        data.resume_id,
        job_description,
        job_title,
    )

    return TaskIdResponse(task_id=task_id)
