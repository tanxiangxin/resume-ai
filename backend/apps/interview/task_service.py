"""面试轮次与面试集合摘要生成后台任务服务。"""

import asyncio
import json
import logging
import uuid
from datetime import datetime

from pydantic import Field, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chiren_backend.platform.db import async_session
from chiren_backend.platform.llm import call_structured_json
from chiren_backend.platform.llm.client import SupportsStreamingMessages
from chiren_backend.platform.models import (
    SHANGHAI_TZ,
    ConversationMessageRecord,
    InterviewCollection,
    InterviewRound,
    Resume,
)
from chiren_backend.platform.task_state import (
    cleanup_task,
    create_task,
    update_task_error,
    update_task_result,
    update_task_status,
)
from chiren_backend.platform.work_records import (
    build_work_record,
    find_work_by_meta,
    update_work_status,
)
from shared.types.messages import ContentBlock, ConversationMessage, TextBlock
from shared.types.strict_model import StrictBaseModel
from shared.types.task import TaskStatus, TaskType

log = logging.getLogger(__name__)

MAX_RETRIES = 3
content_adapter = TypeAdapter(list[ContentBlock])

INTERVIEW_SUMMARY_SYSTEM = """\
You are a professional interview evaluator. Your task is to review a complete interview
conversation and produce a concise assessment of the candidate's performance.

Below is the JSON schema you must follow:
<json_schema>
{json_schema}
</json_schema>

Important rules:
- Return valid JSON only — no additional text, explanations, or commentary
- Base your assessment entirely on the actual conversation content
- Score should reflect overall performance: 0-39 (poor), 40-59 (below average),
  60-79 (solid), 80-100 (exceptional)
- Strengths and weaknesses must each have 2-5 concrete, specific points
- Write the overall assessment in the same language the interview was conducted in
  (Chinese or English)"""


COLLECTION_SUMMARY_SYSTEM = """\
You are a senior HR evaluator and hiring committee member. Your task is to synthesize
the results from multiple interview rounds and produce a comprehensive overall assessment
of the candidate.

Below is the JSON schema you must follow:
<json_schema>
{json_schema}
</json_schema>

Important rules:
- Return valid JSON only — no additional text, explanations, or commentary
- Base your assessment entirely on the provided interview round summaries
- overall_score should NOT be a simple average — weigh different rounds appropriately
  (e.g., technical rounds and Leader rounds carry more weight)
- key_strengths and key_weaknesses must synthesize patterns across rounds,
  not simply concatenate each round's individual points
- dimension_breakdown must merge overlapping assessment dimensions from different
  rounds into unified category scores (e.g., "技术深度" mentioned in both technical
  and project rounds should be scored once, drawing on all relevant evidence)
- recommendation should be one of: "strong_hire", "hire", "neutral", "no_hire",
  "strong_no_hire", expressed in the same language as the interview content
- risk_flags should identify red flags that span multiple rounds or are severe
  enough to warrant attention (e.g., salary mismatch, experience fabrication,
  consistent poor communication)
- Write the overall_assessment in the same language the interview was conducted in
  (Chinese or English)"""


class InterviewRoundSummary(StrictBaseModel):
    """面试轮次摘要数据结构。"""

    overall_assessment: str = Field(description="Overall performance assessment")
    strengths: list[str] = Field(description="Key strengths demonstrated")
    weaknesses: list[str] = Field(description="Areas for improvement")
    score: int = Field(ge=0, le=100, description="Overall score (0-100)")


class DimensionScore(StrictBaseModel):
    """按能力维度评分。"""

    dimension: str = Field(
        description="Dimension name, e.g. 'Technical Foundation', 'Communication'"
    )
    score: int = Field(ge=0, le=100, description="Score for this dimension (0-100)")
    comment: str = Field(default="", description="Brief comment on this dimension")


class RoundSummaryReference(StrictBaseModel):
    """对单个轮次摘要的引用。"""

    round_id: str = Field(description="Round ID")
    round_name: str = Field(description="Round name, e.g. 'Technical Interview'")
    interviewer_name: str = Field(description="Interviewer name")
    interviewer_title: str = Field(description="Interviewer title")
    score: int = Field(ge=0, le=100, description="Score for this round (0-100)")
    key_points: list[str] = Field(
        default_factory=list,
        description="1-3 key takeaways extracted from this round's summary",
    )


class InterviewCollectionSummary(StrictBaseModel):
    """面试集合总体总结数据结构。"""

    overall_score: int = Field(
        ge=0, le=100, description="Overall composite score (0-100)"
    )
    overall_assessment: str = Field(description="Overall assessment (multi-paragraph)")
    round_summaries: list[RoundSummaryReference] = Field(
        description="References to each round's summary"
    )
    key_strengths: list[str] = Field(
        description="Key strengths synthesized across rounds"
    )
    key_weaknesses: list[str] = Field(
        description="Key weaknesses synthesized across rounds"
    )
    dimension_breakdown: list[DimensionScore] = Field(
        description="Score breakdown by competency dimension"
    )
    recommendation: str = Field(
        description="Hiring recommendation: strong_hire/hire/neutral/no_hire/strong_no_hire"
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Risk flags (e.g. experience mismatch, stability concerns)",
    )


async def _load_round_messages(
    round_id: str, db: AsyncSession
) -> list[ConversationMessage]:
    """加载指定轮次的所有对话消息。

    Args:
        round_id: 面试轮次 ID（即 conversation_id）。
        db: 数据库会话。

    Returns:
        按时间排序的对话消息列表。
    """
    stmt = (
        select(ConversationMessageRecord)
        .where(ConversationMessageRecord.conversation_id == round_id)
        .order_by(ConversationMessageRecord.created_at.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    messages: list[ConversationMessage] = []
    for rec in records:
        try:
            content = content_adapter.validate_python(
                json.loads(rec.content) if rec.content else []
            )
        except (json.JSONDecodeError, TypeError, ValidationError):
            content = [TextBlock(text=rec.content or "")]
        messages.append(ConversationMessage(role=rec.role, content=content))
    return messages


def _build_summary_prompt(messages: list[ConversationMessage]) -> str:
    """构建发给 LLM 的摘要请求。

    Args:
        messages: 该轮的所有对话消息。

    Returns:
        LLM 用户消息内容。
    """
    conversation_text_parts: list[str] = []
    for msg in messages:
        texts: list[str] = []
        for block in msg.content:
            if hasattr(block, "text") and block.text:
                texts.append(block.text)
        if texts:
            prefix = "面试官" if msg.role == "assistant" else "候选人"
            conversation_text_parts.append(f"{prefix}: {' '.join(texts)}")

    conversation_text = "\n\n".join(conversation_text_parts)

    if not conversation_text.strip():
        conversation_text = "（无对话记录）"

    return f"""Please analyze the following interview conversation and provide a concise
performance summary.

Interview conversation:
---
{conversation_text}
---

Generate the assessment based on the conversation above."""


async def _call_llm_for_summary(
    client: SupportsStreamingMessages,
    model: str,
    messages: list[ConversationMessage],
) -> InterviewRoundSummary:
    """调用 LLM 生成面试摘要。

    Args:
        client: LLM API 客户端。
        model: 模型名称。
        messages: 该轮的所有对话消息。

    Returns:
        解析后的面试摘要。

    Raises:
        Exception: LLM 调用失败或解析失败。
    """
    schema_json = json.dumps(
        InterviewRoundSummary.model_json_schema(), ensure_ascii=False
    )

    system_prompt = INTERVIEW_SUMMARY_SYSTEM.format(json_schema=schema_json)
    user_prompt = _build_summary_prompt(messages)
    try:
        return await call_structured_json(
            client,
            model,
            system_prompt,
            user_prompt,
            InterviewRoundSummary,
            max_retries=MAX_RETRIES,
            max_tokens=2048,
            temperature=0.5,
            invalid_response_prefix="Invalid response format",
        )
    except (ValidationError, json.JSONDecodeError) as e:
        raise Exception(f"LLM 摘要解析失败: {e}") from e


async def run_round_summary_task(
    db: AsyncSession,
    task_id: str,
    round_id: str,
    client: SupportsStreamingMessages,
    model: str,
) -> None:
    """执行面试轮次摘要生成的后台任务。

    Args:
        db: 数据库会话。
        task_id: 任务 ID（对应 BaseWork.id）。
        round_id: 面试轮次 ID。
        client: LLM API 客户端。
        model: 模型名称。
    """
    try:
        await update_work_status(db, task_id, TaskStatus.RUNNING)
        await update_task_status(task_id, TaskStatus.RUNNING)

        result = await db.execute(
            select(InterviewRound)
            .where(InterviewRound.id == round_id)
            .with_for_update()
        )
        round_obj = result.scalar_one_or_none()
        if round_obj is None:
            raise Exception(f"面试轮次不存在: {round_id}")

        existing_summary = (round_obj.meta_info or {}).get("round_summary")
        if existing_summary is not None:
            await update_work_status(db, task_id, TaskStatus.SUCCESS)
            await update_task_result(task_id, {"round_id": round_id, "skipped": True})
            asyncio.create_task(cleanup_task(task_id, None))
            return

        messages = await _load_round_messages(round_id, db)

        if not messages:
            raise Exception("该轮次没有对话记录，无法生成摘要")

        summary = await _call_llm_for_summary(client, model, messages)

        meta_info = round_obj.meta_info or {}
        meta_info["round_summary"] = {
            "overall_assessment": summary.overall_assessment,
            "strengths": summary.strengths,
            "weaknesses": summary.weaknesses,
            "score": summary.score,
            "generated_at": datetime.now(SHANGHAI_TZ).isoformat(),
        }
        round_obj.meta_info = meta_info

        await db.commit()

        await update_work_status(db, task_id, TaskStatus.SUCCESS)
        await update_task_result(task_id, {"round_id": round_id})

        asyncio.create_task(cleanup_task(task_id, None))

    except Exception as e:
        await db.rollback()
        log.exception("Interview summary task failed: %s", e)
        await update_work_status(
            db, task_id, TaskStatus.ERROR, f"摘要生成失败: {str(e)}"
        )
        await update_task_error(task_id, f"run_round_summary_task error: {str(e)}")
        asyncio.create_task(cleanup_task(task_id, None))
        raise


async def _load_collection_round_summaries(
    collection_id: str, db: AsyncSession
) -> tuple[list[dict], list[InterviewRound]]:
    """加载面试集合中所有已完成轮次的摘要数据。

    Args:
        collection_id: 面试集合 ID。
        db: 数据库会话。

    Returns:
        (各轮次摘要信息列表, 缺失摘要的已完成轮次列表)。
    """
    stmt = (
        select(InterviewRound)
        .where(InterviewRound.interview_collection_id == collection_id)
        .order_by(InterviewRound.sort_order.asc())
    )
    result = await db.execute(stmt)
    rounds = result.scalars().all()

    summaries: list[dict] = []
    missing: list[InterviewRound] = []

    for r in rounds:
        round_summary = (r.meta_info or {}).get("round_summary")
        if r.status != "completed":
            continue
        if round_summary is None:
            missing.append(r)
            continue
        summaries.append(
            {
                "round_id": r.id,
                "round_name": r.name,
                "interviewer_name": r.interviewer_name,
                "interviewer_title": r.interviewer_title,
                "assessment_dimensions": _parse_json_array(r.assessment_dimensions),
                "score": round_summary.get("score"),
                "overall_assessment": round_summary.get("overall_assessment", ""),
                "strengths": round_summary.get("strengths", []),
                "weaknesses": round_summary.get("weaknesses", []),
            }
        )

    return summaries, missing


def _parse_json_array(value: str | list | None) -> list:
    """安全解析 JSON 数组字符串。

    Args:
        value: JSON 字符串、列表或 None。

    Returns:
        解析后的列表。
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _build_collection_summary_prompt(
    collection_name: str,
    round_summaries: list[dict],
    jd_text: str | None,
) -> str:
    """构建面试集合总结的 LLM 请求。

    Args:
        collection_name: 面试集合名称。
        round_summaries: 各轮次摘要数据。
        jd_text: 岗位描述文本。

    Returns:
        LLM 用户消息内容。
    """
    parts: list[str] = []
    parts.append(f"面试方案: {collection_name}")

    if jd_text:
        parts.append(f"\n岗位描述:\n---\n{jd_text}\n---")

    parts.append("\n各轮面试摘要:")

    for i, s in enumerate(round_summaries, 1):
        parts.append(
            f"\n## 第{i}轮: {s['round_name']}"
            f"\n- 面试官: {s['interviewer_name']} ({s['interviewer_title']})"
            f"\n- 考察维度: {', '.join(s.get('assessment_dimensions', []))}"
            f"\n- 评分: {s['score']}/100"
            f"\n- 综合评价: {s.get('overall_assessment', '')}"
            f"\n- 优势: {', '.join(s.get('strengths', []))}"
            f"\n- 劣势: {', '.join(s.get('weaknesses', []))}"
        )

    parts.append("\n\n请根据以上各轮面试摘要，生成整体的面试总结。")

    return "\n".join(parts)


async def _call_llm_for_collection_summary(
    client: SupportsStreamingMessages,
    model: str,
    collection_name: str,
    round_summaries: list[dict],
    jd_text: str | None,
) -> InterviewCollectionSummary:
    """调用 LLM 生成面试集合总结。

    Args:
        client: LLM API 客户端。
        model: 模型名称。
        collection_name: 面试集合名称。
        round_summaries: 各轮次摘要数据。
        jd_text: 岗位描述文本。

    Returns:
        解析后的面试集合总结。

    Raises:
        Exception: LLM 调用失败或解析失败。
    """
    schema_json = json.dumps(
        InterviewCollectionSummary.model_json_schema(), ensure_ascii=False
    )

    system_prompt = COLLECTION_SUMMARY_SYSTEM.format(json_schema=schema_json)
    user_prompt = _build_collection_summary_prompt(
        collection_name, round_summaries, jd_text
    )
    try:
        return await call_structured_json(
            client,
            model,
            system_prompt,
            user_prompt,
            InterviewCollectionSummary,
            max_retries=MAX_RETRIES,
            max_tokens=4096,
            temperature=0.5,
            invalid_response_prefix="Invalid response format",
        )
    except (ValidationError, json.JSONDecodeError) as e:
        raise Exception(f"LLM 集合总结解析失败: {e}") from e


async def _run_round_summary_task_isolated(
    task_id: str,
    round_id: str,
    client: SupportsStreamingMessages,
    model: str,
) -> None:
    """在独立数据库会话中执行轮次摘要任务。

    Args:
        task_id: 任务 ID（对应 BaseWork.id）。
        round_id: 面试轮次 ID。
        client: LLM API 客户端。
        model: 模型名称。
    """
    async with async_session() as session:
        await run_round_summary_task(session, task_id, round_id, client, model)


async def run_collection_summary_task(
    db: AsyncSession,
    task_id: str,
    collection_id: str,
    client: SupportsStreamingMessages,
    model: str,
) -> None:
    """执行面试集合总体总结生成的后台任务。

    优先确保所有已完成轮次都已生成 round_summary，
    缺失的轮次通过并发子任务自动补全。补全失败则整体任务失败。

    Args:
        db: 数据库会话。
        task_id: 任务 ID（对应 BaseWork.id）。
        collection_id: 面试集合 ID。
        client: LLM API 客户端。
        model: 模型名称。
    """
    try:
        await update_work_status(db, task_id, TaskStatus.RUNNING)
        await update_task_status(task_id, TaskStatus.RUNNING)

        stmt = select(InterviewCollection).where(
            InterviewCollection.id == collection_id
        )
        result = await db.execute(stmt)
        collection = result.scalar_one_or_none()
        if collection is None:
            raise Exception(f"面试集合不存在: {collection_id}")

        summaries, missing = await _load_collection_round_summaries(collection_id, db)

        if not summaries and not missing:
            raise Exception("该面试集合没有已完成的轮次")

        if missing:
            missing_names = ", ".join(r.name for r in missing)
            log.info(
                "Collection %s: %d round(s) missing summaries, auto-generating: %s",
                collection_id,
                len(missing),
                missing_names,
            )

            round_coroutines: list[tuple[str, asyncio.Task[None]]] = []
            for r in missing:
                existing_task = await find_work_by_meta(
                    db,
                    TaskType.INTERVIEW_SUMMARY,
                    "round_id",
                    r.id,
                )
                if existing_task is not None:
                    continue

                round_task_id = str(uuid.uuid4())
                work = build_work_record(
                    round_task_id,
                    TaskType.INTERVIEW_SUMMARY,
                    {"round_id": r.id},
                )
                db.add(work)
                await db.commit()
                create_task(round_task_id, TaskType.INTERVIEW_SUMMARY)
                round_coroutines.append(
                    (
                        r.name,
                        asyncio.create_task(
                            _run_round_summary_task_isolated(
                                round_task_id, r.id, client, model
                            )
                        ),
                    )
                )

            if round_coroutines:
                gathered = await asyncio.gather(
                    *[c for _, c in round_coroutines],
                    return_exceptions=True,
                )

                failed = [
                    (name, exc)
                    for (name, _), exc in zip(round_coroutines, gathered)
                    if isinstance(exc, BaseException)
                ]
                if failed:
                    for name, exc in failed:
                        log.error(
                            "Round summary auto-generation failed for %s: %s",
                            name,
                            exc,
                        )
                    raise Exception(
                        "以下轮次摘要自动生成失败: "
                        f"{', '.join(f'{name}({exc})' for name, exc in failed)}"
                    )

            summaries, _ = await _load_collection_round_summaries(collection_id, db)

        if not summaries:
            raise Exception("该面试集合没有可用的轮次摘要")

        resume_stmt = select(Resume).where(Resume.id == collection.sub_resume_id)
        resume_result = await db.execute(resume_stmt)
        resume = resume_result.scalar_one_or_none()

        jd_text: str | None = None
        if resume is not None and resume.meta_info:
            jd_text = resume.meta_info.get("job_description")

        summary = await _call_llm_for_collection_summary(
            client, model, collection.name, summaries, jd_text
        )

        meta_info = collection.meta_info or {}
        meta_info["collection_summary"] = {
            "overall_score": summary.overall_score,
            "overall_assessment": summary.overall_assessment,
            "round_summaries": [
                rs.model_dump(mode="json") for rs in summary.round_summaries
            ],
            "key_strengths": summary.key_strengths,
            "key_weaknesses": summary.key_weaknesses,
            "dimension_breakdown": [
                ds.model_dump(mode="json") for ds in summary.dimension_breakdown
            ],
            "recommendation": summary.recommendation,
            "risk_flags": summary.risk_flags,
            "generated_at": datetime.now(SHANGHAI_TZ).isoformat(),
        }
        collection.meta_info = meta_info

        await db.commit()

        await update_work_status(db, task_id, TaskStatus.SUCCESS)
        await update_task_result(task_id, {"collection_id": collection_id})

        asyncio.create_task(cleanup_task(task_id, None))

    except Exception as e:
        await db.rollback()
        log.exception("Collection summary task failed: %s", e)
        await update_work_status(
            db, task_id, TaskStatus.ERROR, f"集合总结生成失败: {str(e)}"
        )
        await update_task_error(task_id, f"run_collection_summary_task error: {str(e)}")
        asyncio.create_task(cleanup_task(task_id, None))
        raise
