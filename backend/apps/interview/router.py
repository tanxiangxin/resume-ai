"""面试模块路由"""

import json
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
)
from pydantic import BaseModel, ConfigDict, alias_generators
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette import EventSourceResponse

from apps.interview.chat import interview_chat
from apps.interview.schemas import (
    BUILT_IN_INTERVIEWERS,
    BuiltInInterviewerResponse,
    BuiltInInterviewerType,
    InterviewChatRequest,
    InterviewCollectionCreate,
    InterviewCollectionCreateWithRounds,
    InterviewRoundCreate,
    InterviewRoundUpdate,
)
from apps.interview.service import (
    resolve_interviewer_profile,
    update_collection_status_by_rounds,
    validate_round_config_update,
    validate_round_creation,
    validate_round_status_change,
    validate_sub_resume,
)
from apps.interview.task_service import (
    run_collection_summary_task,
    run_round_summary_task,
)
from chiren_backend.platform.db import get_session
from chiren_backend.platform.llm import get_client
from chiren_backend.platform.models import InterviewCollection, InterviewRound, Resume
from chiren_backend.platform.task_state import create_task
from chiren_backend.platform.work_records import build_work_record, find_work_by_meta
from shared.types.interview import InterviewCollectionSchema, InterviewRoundSchema
from shared.types.task import TaskType
from shared.types.work import TaskIdResponse

router = APIRouter(prefix="/interview", tags=["interview"])


class UpdateRoundStatusRequest(BaseModel):
    """更新面试轮次状态请求"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    round_id: str
    status: str


@router.get("/built-in-interviewers", summary="获取内置面试官列表")
async def get_built_in_interviewers():
    """返回所有内置面试官资料，按固定顺序排列。

    顺序按一般面试流程排列：HR → 技术 → 场景 → 项目深挖 → 行为 → Leader。
    """
    order = [
        BuiltInInterviewerType.HR,
        BuiltInInterviewerType.TECHNICAL,
        BuiltInInterviewerType.SCENARIO,
        BuiltInInterviewerType.PROJECT,
        BuiltInInterviewerType.BEHAVIORAL,
        BuiltInInterviewerType.LEADER,
    ]
    return [
        BuiltInInterviewerResponse(
            type=interviewer_type.value,
            name=profile.name,
            title=profile.title,
            round_name=profile.round_name,
            bio=profile.bio,
            question_style=profile.question_style,
            assessment_dimensions=profile.assessment_dimensions,
            personality_traits=profile.personality_traits,
            avatar_color=profile.avatar_color,
            avatar_text=profile.avatar_text,
        )
        for interviewer_type in order
        if (profile := BUILT_IN_INTERVIEWERS.get(interviewer_type)) is not None
    ]


@router.post("/collection", summary="创建面试集合")
async def create_collection(
    request: Annotated[InterviewCollectionCreate, Body()],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> InterviewCollectionSchema:
    await validate_sub_resume(request.sub_resume_id, db)
    collection = InterviewCollection(
        name=request.name,
        sub_resume_id=request.sub_resume_id,
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return collection.to_pydantic()


@router.post("/collection/with-rounds", summary="创建面试集合（含多个轮次）")
async def create_collection_with_rounds(
    request: Annotated[InterviewCollectionCreateWithRounds, Body()],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> InterviewCollectionSchema:
    await validate_sub_resume(request.sub_resume_id, db)

    collection = InterviewCollection(
        name=request.name,
        sub_resume_id=request.sub_resume_id,
    )
    db.add(collection)
    await db.flush()

    for i, draft in enumerate(request.rounds):
        profile = resolve_interviewer_profile(draft)
        if profile is not None:
            interviewer_name = profile.name
            interviewer_title = profile.title
            interviewer_bio = profile.bio
            question_style = profile.question_style
            assessment_dimensions = profile.assessment_dimensions
            personality_traits = profile.personality_traits
        else:
            interviewer_name = draft.interviewer_name
            interviewer_title = draft.interviewer_title
            interviewer_bio = draft.interviewer_bio
            question_style = draft.question_style
            assessment_dimensions = draft.assessment_dimensions
            personality_traits = draft.personality_traits

        round_obj = InterviewRound(
            interview_collection_id=collection.id,
            name=draft.name,
            interviewer_name=interviewer_name,
            interviewer_title=interviewer_title or "",
            interviewer_bio=interviewer_bio or "",
            question_style=question_style or "",
            assessment_dimensions=json.dumps(
                assessment_dimensions or [], ensure_ascii=False
            ),
            personality_traits=json.dumps(personality_traits or [], ensure_ascii=False),
            sort_order=i,
        )
        db.add(round_obj)

    await db.commit()
    await db.refresh(collection)
    return collection.to_pydantic()


@router.get("/collection/list/{sub_resume_id}", summary="获取子简历的面试集合列表")
async def list_collections(
    sub_resume_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[InterviewCollectionSchema]:
    stmt = (
        select(InterviewCollection)
        .where(InterviewCollection.sub_resume_id == sub_resume_id)
        .options(selectinload(InterviewCollection.rounds))
        .order_by(InterviewCollection.created_at.desc())
    )
    result = await db.execute(stmt)
    collections = result.scalars().all()
    return [c.to_pydantic() for c in collections]


@router.get("/collection/{collection_id}", summary="获取面试集合详情")
async def get_collection(
    collection_id: Annotated[str, Path(description="面试集合ID")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[InterviewRoundSchema]:
    stmt = (
        select(InterviewCollection)
        .where(InterviewCollection.id == collection_id)
        .options(selectinload(InterviewCollection.rounds))
    )
    result = await db.execute(stmt)
    collection = result.scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=404, detail="面试集合不存在")
    return [
        r.to_pydantic() for r in sorted(collection.rounds, key=lambda r: r.sort_order)
    ]


@router.post("/round", summary="创建面试轮次")
async def create_round(
    request: Annotated[InterviewRoundCreate, Body(description="创建面试轮次请求参数")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> InterviewRoundSchema:
    """为现有面试集合添加一个新轮次。

    已完成的集合不允许添加轮次。
    新轮次默认放到最后（sort_order 自动递增）。
    """
    collection = await validate_round_creation(request.interview_collection_id, db)

    if request.sort_order is None:
        stmt = (
            select(InterviewRound.sort_order)
            .where(
                InterviewRound.interview_collection_id
                == request.interview_collection_id
            )
            .order_by(InterviewRound.sort_order.desc())
        )
        result = await db.execute(stmt)
        max_order = result.scalar_one_or_none()
        request.sort_order = (max_order or -1) + 1

    round_obj = InterviewRound(
        interview_collection_id=request.interview_collection_id,
        name=request.name,
        interviewer_name=request.interviewer_name,
        interviewer_title=request.interviewer_title or "",
        interviewer_bio=request.interviewer_bio or "",
        question_style=request.question_style or "",
        assessment_dimensions=json.dumps(
            request.assessment_dimensions or [], ensure_ascii=False
        ),
        personality_traits=json.dumps(
            request.personality_traits or [], ensure_ascii=False
        ),
        sort_order=request.sort_order,
    )
    db.add(round_obj)
    await db.flush()

    if collection.status == "completed":
        collection.status = "not_started"

    await db.commit()
    await db.refresh(round_obj)
    return round_obj.to_pydantic()


@router.delete("/collection/delete", summary="删除面试集合")
async def delete_collection(
    id: Annotated[str, Query(description="面试集合ID")],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    stmt = select(InterviewCollection).where(InterviewCollection.id == id)
    result = await db.execute(stmt)
    collection = result.scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=404, detail="面试集合不存在")
    await db.delete(collection)
    await db.commit()
    return None


@router.put("/round/update", summary="更新面试轮次配置")
async def update_round(
    request: Annotated[InterviewRoundUpdate, Body(description="面试轮次更新请求参数")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> InterviewRoundSchema:
    """更新面试轮次的配置信息。

    仅允许修改 status 为 not_started 的轮次，
    防止面试进行中或已完成后改变规则导致数据不一致。
    """
    round_obj = await validate_round_config_update(request.id, db)

    if request.name is not None:
        round_obj.name = request.name
    if request.interviewer_name is not None:
        round_obj.interviewer_name = request.interviewer_name
    if request.interviewer_title is not None:
        round_obj.interviewer_title = request.interviewer_title
    if request.interviewer_bio is not None:
        round_obj.interviewer_bio = request.interviewer_bio
    if request.question_style is not None:
        round_obj.question_style = request.question_style
    if request.assessment_dimensions is not None:
        round_obj.assessment_dimensions = json.dumps(
            request.assessment_dimensions, ensure_ascii=False
        )
    if request.personality_traits is not None:
        round_obj.personality_traits = json.dumps(
            request.personality_traits, ensure_ascii=False
        )
    if request.sort_order is not None:
        round_obj.sort_order = request.sort_order

    await db.commit()
    await db.refresh(round_obj)
    return round_obj.to_pydantic()


@router.put("/round/status", summary="更新面试轮次状态")
async def update_round_status(
    request: Annotated[
        UpdateRoundStatusRequest, Body(description="面试轮次状态更新请求参数")
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> InterviewRoundSchema:
    # First find the round to get its collection_id
    stmt = select(InterviewRound).where(InterviewRound.id == request.round_id)
    result = await db.execute(stmt)
    round_obj = result.scalar_one_or_none()
    if round_obj is None:
        raise HTTPException(status_code=404, detail="面试轮次不存在")

    # Validate status change with correct collection_id
    await validate_round_status_change(
        collection_id=round_obj.interview_collection_id,
        round_id=request.round_id,
        target_status=request.status,
        db=db,
    )

    # Update status
    round_obj.status = request.status
    await db.flush()

    # Update collection status based on rounds
    await update_collection_status_by_rounds(round_obj.interview_collection_id, db)

    await db.commit()
    await db.refresh(round_obj)
    return round_obj.to_pydantic()


@router.post("/round/{round_id}/chat", summary="面试对话接口")
async def round_chat(
    round_id: Annotated[str, Path(description="面试轮次ID")],
    request: Annotated[InterviewChatRequest, Body(description="面试对话请求参数")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EventSourceResponse:
    stmt = select(InterviewRound).where(InterviewRound.id == round_id)
    result = await db.execute(stmt)
    round = result.scalar_one_or_none()
    if round is None:
        raise HTTPException(status_code=404, detail="面试轮次不存在")

    if request.action == "start":
        collection_stmt = select(InterviewCollection).where(
            InterviewCollection.id == round.interview_collection_id
        )
        collection_result = await db.execute(collection_stmt)
        collection = collection_result.scalar_one_or_none()
        if collection is None:
            raise HTTPException(status_code=404, detail="面试集合不存在")

        resume_stmt = select(Resume).where(Resume.id == collection.sub_resume_id)
        resume_result = await db.execute(resume_stmt)
        resume = resume_result.scalar_one_or_none()
        if (
            resume is None
            or not resume.meta_info
            or not resume.meta_info.get("job_description")
        ):
            raise HTTPException(
                status_code=400,
                detail="子简历缺少岗位描述(JD)，无法开始面试",
            )

        await validate_round_status_change(
            collection_id=round.interview_collection_id,
            round_id=round_id,
            target_status="in_progress",
            db=db,
        )
        round.status = "in_progress"
        await db.flush()
        await update_collection_status_by_rounds(round.interview_collection_id, db)
        await db.commit()
    elif round.status != "in_progress":
        raise HTTPException(
            status_code=400,
            detail="面试尚未开始或已结束",
        )

    async def generate():
        api_client = get_client(request.type, request.api_key, request.base_url)
        async for sse in interview_chat(round, request, api_client, db):
            yield sse

    return EventSourceResponse(generate())


@router.delete("/round/delete", summary="删除面试轮次")
async def delete_round(
    id: Annotated[str, Query(description="面试轮次ID")],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    stmt = select(InterviewRound).where(InterviewRound.id == id)
    result = await db.execute(stmt)
    round_obj = result.scalar_one_or_none()
    if round_obj is None:
        raise HTTPException(status_code=404, detail="面试轮次不存在")
    await db.delete(round_obj)
    await db.commit()
    return None


class RegenerateSummaryRequest(BaseModel):
    """手动重新生成面试摘要请求"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    type: str
    api_key: str
    base_url: str | None = None
    model: str


@router.post(
    "/round/{round_id}/regenerate-summary",
    summary="手动重新生成面试轮次摘要",
)
async def regenerate_summary(
    round_id: Annotated[str, Path(description="面试轮次ID")],
    request: Annotated[RegenerateSummaryRequest, Body(description="摘要生成请求参数")],
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskIdResponse:
    """为已完成的面试轮次手动触发摘要生成，用于重试失败的摘要任务。

    要求轮次状态为 completed。
    """
    stmt = select(InterviewRound).where(InterviewRound.id == round_id)
    result = await db.execute(stmt)
    round_obj = result.scalar_one_or_none()
    if round_obj is None:
        raise HTTPException(status_code=404, detail="面试轮次不存在")
    if round_obj.status != "completed":
        raise HTTPException(status_code=400, detail="只有已完成的面试轮次才能生成摘要")

    existing_task = await find_work_by_meta(
        db,
        TaskType.INTERVIEW_SUMMARY,
        "round_id",
        round_id,
    )
    if existing_task is not None:
        return TaskIdResponse(task_id=existing_task.id)

    task_id = str(uuid.uuid4())

    work = build_work_record(
        task_id, TaskType.INTERVIEW_SUMMARY, {"round_id": round_id}
    )
    db.add(work)
    await db.commit()
    create_task(task_id, TaskType.INTERVIEW_SUMMARY)

    client = get_client(request.type, request.api_key, request.base_url)

    background_tasks.add_task(
        run_round_summary_task,
        db,
        task_id,
        round_id,
        client,
        request.model,
    )

    return TaskIdResponse(task_id=task_id)


@router.post(
    "/collection/{collection_id}/regenerate-summary",
    summary="手动生成/重新生成面试集合总体总结",
)
async def regenerate_collection_summary(
    collection_id: Annotated[str, Path(description="面试集合ID")],
    request: Annotated[RegenerateSummaryRequest, Body(description="总结生成请求参数")],
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskIdResponse:
    """为面试集合手动触发总体总结生成。

    要求集合状态为 completed。若某些已完成轮次尚未生成摘要，
    后台任务会自动并发补全，补全失败则整体任务失败。
    """
    stmt = (
        select(InterviewCollection)
        .where(InterviewCollection.id == collection_id)
        .options(selectinload(InterviewCollection.rounds))
    )
    result = await db.execute(stmt)
    collection = result.scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=404, detail="面试集合不存在")
    if collection.status != "completed":
        raise HTTPException(
            status_code=400, detail="只有已完成的面试集合才能生成总体总结"
        )

    existing_task = await find_work_by_meta(
        db,
        TaskType.COLLECTION_SUMMARY,
        "collection_id",
        collection_id,
    )
    if existing_task is not None:
        return TaskIdResponse(task_id=existing_task.id)

    task_id = str(uuid.uuid4())

    work = build_work_record(
        task_id,
        TaskType.COLLECTION_SUMMARY,
        {"collection_id": collection_id},
    )
    db.add(work)
    await db.commit()
    create_task(task_id, TaskType.COLLECTION_SUMMARY)

    client = get_client(request.type, request.api_key, request.base_url)

    background_tasks.add_task(
        run_collection_summary_task,
        db,
        task_id,
        collection_id,
        client,
        request.model,
    )

    return TaskIdResponse(task_id=task_id)
