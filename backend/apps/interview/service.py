"""面试模块业务逻辑服务

提供面试集合和面试轮次的状态流转校验，
以及内置面试官资料解析逻辑。
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.interview.schemas import (
    BUILT_IN_INTERVIEWERS,
    BuiltInInterviewerProfile,
    InterviewRoundDraft,
)
from chiren_backend.platform.models import InterviewCollection, InterviewRound, Resume

VALID_STATUS_TRANSITIONS = {
    "not_started": ["in_progress"],
    "in_progress": ["completed"],
    "completed": [],
}


def validate_status_transition(current: str, target: str) -> None:
    """校验单个状态流转的合法性。

    Args:
        current: 当前状态
        target: 目标状态

    Raises:
        HTTPException: 状态流转不合法时抛出 400 错误
    """
    allowed = VALID_STATUS_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise HTTPException(
            status_code=400, detail=f"Invalid status transition: {current} -> {target}"
        )


async def validate_sub_resume(sub_resume_id: str, db: AsyncSession) -> None:
    """校验子简历是否存在且确实为子简历。

    子简历的特征是其 workspace_id 不为空（不是顶级 Workspace）。

    Args:
        sub_resume_id: 子简历 ID
        db: 数据库会话

    Raises:
        HTTPException(404): 简历不存在
        HTTPException(400): 简历不是子简历（workspace_id 为空）
    """
    stmt = select(Resume).where(Resume.id == sub_resume_id)
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail=f"子简历不存在: {sub_resume_id}")
    if resume.workspace_id is None:
        raise HTTPException(
            status_code=400, detail=f"该简历不是子简历: {sub_resume_id}"
        )


async def validate_round_creation(
    collection_id: str,
    db: AsyncSession,
) -> InterviewCollection:
    """校验添加轮次的合法性。

    已完成的面试集合不允许再添加轮次，防止修改已结束的历史记录。

    Args:
        collection_id: 所属面试集合 ID
        db: 数据库会话

    Returns:
        校验通过则返回集合对象

    Raises:
        HTTPException(404): 集合不存在
        HTTPException(400): 集合已完成，不允许添加轮次
    """
    stmt = select(InterviewCollection).where(InterviewCollection.id == collection_id)
    result = await db.execute(stmt)
    collection = result.scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=404, detail=f"面试集合不存在: {collection_id}")
    if collection.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="该面试方案已完成，不允许再添加轮次",
        )
    return collection


async def validate_round_config_update(
    round_id: str,
    db: AsyncSession,
) -> InterviewRound:
    """校验轮次配置更新的合法性。

    只有 not_started 状态的轮次允许修改配置，
    防止面试进行中或已完成后改变规则导致数据不一致。

    Args:
        round_id: 轮次 ID
        db: 数据库会话

    Returns:
        校验通过则返回该轮次对象

    Raises:
        HTTPException(404): 轮次不存在
        HTTPException(400): 轮次状态不允许修改配置
    """
    stmt = select(InterviewRound).where(InterviewRound.id == round_id)
    result = await db.execute(stmt)
    round_obj = result.scalar_one_or_none()
    if round_obj is None:
        raise HTTPException(status_code=404, detail=f"面试轮次不存在: {round_id}")

    if round_obj.status != "not_started":
        status_label = {
            "in_progress": "进行中",
            "completed": "已完成",
        }.get(round_obj.status, round_obj.status)
        raise HTTPException(
            status_code=400,
            detail=f"轮次状态为「{status_label}」，不允许修改配置",
        )
    return round_obj


async def validate_round_reorder(
    collection_id: str,
    db: AsyncSession,
) -> None:
    """校验调整轮次顺序的合法性。

    当集合中存在任意 in_progress 的轮次时，禁止调整顺序，
    防止破坏顺序依赖导致状态流转异常。

    Args:
        collection_id: 面试集合 ID
        db: 数据库会话

    Raises:
        HTTPException(400): 存在进行中的轮次
    """
    stmt = select(InterviewRound).where(
        InterviewRound.interview_collection_id == collection_id,
        InterviewRound.status == "in_progress",
    )
    result = await db.execute(stmt)
    in_progress_round = result.scalar_one_or_none()
    if in_progress_round is not None:
        raise HTTPException(
            status_code=400,
            detail=f"轮次「{in_progress_round.name}」正在进行中，无法调整顺序",
        )


async def validate_round_status_change(
    collection_id: str,
    round_id: str,
    target_status: str,
    db: AsyncSession,
) -> InterviewRound:
    """校验轮次状态变更的合法性。

    规则:
    1. 目标状态必须遵循 not_started -> in_progress -> completed 流转
    2. 转为 in_progress 时，集合中不能有其他轮次正在 in_progress
    3. 转为 in_progress 时，所有 sort_order 更小的轮次必须已完成
    4. 集合状态必须允许此操作

    Args:
        collection_id: 所属面试集合 ID
        round_id: 轮次 ID
        target_status: 目标状态
        db: 数据库会话

    Returns:
        校验通过则返回该轮次对象

    Raises:
        HTTPException(404): 轮次或集合不存在
        HTTPException(400): 状态流转不合法
    """
    # 获取轮次
    stmt = select(InterviewRound).where(InterviewRound.id == round_id)
    result = await db.execute(stmt)
    round_obj = result.scalar_one_or_none()
    if round_obj is None:
        raise HTTPException(status_code=404, detail=f"面试轮次不存在: {round_id}")
    if round_obj.interview_collection_id != collection_id:
        raise HTTPException(status_code=400, detail="轮次不属于指定的面试集合")

    # 获取集合
    stmt_col = select(InterviewCollection).where(
        InterviewCollection.id == collection_id
    )
    result_col = await db.execute(stmt_col)
    collection = result_col.scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=404, detail=f"面试集合不存在: {collection_id}")

    # 1. 校验状态流转
    validate_status_transition(round_obj.status, target_status)

    # 2. 转为 in_progress 时的额外校验
    if target_status == "in_progress":
        # 获取集合中的所有轮次
        stmt_all = (
            select(InterviewRound)
            .where(InterviewRound.interview_collection_id == collection_id)
            .order_by(InterviewRound.sort_order)
        )
        result_all = await db.execute(stmt_all)
        all_rounds = result_all.scalars().all()

        # 不能有其他轮次正在 in_progress
        for r in all_rounds:
            if r.id != round_id and r.status == "in_progress":
                raise HTTPException(
                    status_code=400,
                    detail=f"已有轮次正在面试中: {r.name}，请先完成当前轮次",
                )

        # 所有 sort_order 更小的轮次必须已完成
        for r in all_rounds:
            if r.sort_order >= round_obj.sort_order:
                break
            if r.status != "completed":
                raise HTTPException(
                    status_code=400,
                    detail=f"前序轮次未完成: {r.name}，请按顺序进行面试",
                )

    return round_obj


async def update_collection_status_by_rounds(
    collection_id: str, db: AsyncSession
) -> str | None:
    """根据轮次状态自动更新面试集合的状态。

    规则:
    - 如果有任意轮次是 in_progress，集合为 in_progress
    - 如果所有轮次都是 completed，集合为 completed
    - 否则集合保持 not_started

    Args:
        collection_id: 面试集合 ID
        db: 数据库会话

    Returns:
        如果状态发生变化则返回新状态，否则返回 None
    """
    stmt = select(InterviewCollection).where(InterviewCollection.id == collection_id)
    result = await db.execute(stmt)
    collection = result.scalar_one_or_none()
    if collection is None:
        return None

    stmt_rounds = (
        select(InterviewRound)
        .where(InterviewRound.interview_collection_id == collection_id)
        .order_by(InterviewRound.sort_order)
    )
    result_rounds = await db.execute(stmt_rounds)
    rounds = result_rounds.scalars().all()

    if not rounds:
        return None

    statuses = {r.status for r in rounds}

    new_status = collection.status
    if "in_progress" in statuses:
        new_status = "in_progress"
    elif statuses == {"completed"}:
        new_status = "completed"
    elif collection.status == "not_started":
        new_status = "not_started"

    if new_status != collection.status:
        collection.status = new_status
        return new_status
    return None


def resolve_interviewer_profile(
    draft: InterviewRoundDraft,
) -> BuiltInInterviewerProfile | None:
    """Resolve interviewer profile fields from a round draft.

    When the draft specifies ``interviewer_type``, the corresponding built-in
    interviewer profile is returned. When ``interviewer_type`` is None, validates
    that ``interviewer_name`` is provided and returns None (meaning the draft's
    own fields should be used as-is).

    Args:
        draft: Interview round draft with optional interviewer_type.

    Returns:
        The built-in interviewer profile if ``interviewer_type`` is set,
        otherwise None.

    Raises:
        HTTPException: When ``interviewer_type`` is None but
            ``interviewer_name`` is empty.
    """
    if draft.interviewer_type is not None:
        return BUILT_IN_INTERVIEWERS[draft.interviewer_type]

    if not draft.interviewer_name.strip():
        raise HTTPException(
            status_code=400,
            detail="interviewer_type 未设置时，interviewer_name 不能为空",
        )
    return None


async def validate_collection_summary_ready(
    collection_id: str,
    db: AsyncSession,
) -> bool:
    """校验面试集合是否已准备好生成总体总结。

    要求：
    1. 集合状态为 completed
    2. 所有轮次状态为 completed
    3. 所有已完成轮次都已生成 round_summary
    4. 尚未生成过 collection_summary（可重生成）

    Args:
        collection_id: 面试集合 ID。
        db: 数据库会话。

    Returns:
        如果就绪则返回 True。

    Raises:
        HTTPException(400): 条件不满足时抛出。
    """
    from chiren_backend.platform.models import InterviewCollection, InterviewRound

    stmt = select(InterviewCollection).where(InterviewCollection.id == collection_id)
    result = await db.execute(stmt)
    collection = result.scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=404, detail="面试集合不存在")
    if collection.status != "completed":
        raise HTTPException(
            status_code=400, detail="只有已完成的面试集合才能生成总体总结"
        )

    stmt_rounds = (
        select(InterviewRound)
        .where(InterviewRound.interview_collection_id == collection_id)
        .order_by(InterviewRound.sort_order.asc())
    )
    result_rounds = await db.execute(stmt_rounds)
    rounds = result_rounds.scalars().all()

    missing: list[str] = []
    for r in rounds:
        if r.status == "completed":
            round_summary = (r.meta_info or {}).get("round_summary")
            if round_summary is None:
                missing.append(f"{r.name}({r.id})")

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"以下轮次已完成但尚未生成摘要: {', '.join(missing)}",
        )

    return True
