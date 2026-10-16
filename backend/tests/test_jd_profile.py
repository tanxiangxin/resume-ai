"""JD Profile 解析与版本源测试。"""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.jd_profile.formatting import format_jd_profile_for_prompt
from apps.jd_profile.service import (
    ProviderRuntimeConfig,
    _validate_profile_completeness,
    calculate_jd_source_hash,
    ensure_jd_profile,
    parse_jd_profile,
)
from chiren_backend.platform.llm.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiStreamEvent,
    ApiTextDeltaEvent,
)
from chiren_backend.platform.llm.usage import UsageSnapshot
from chiren_backend.platform.models import (
    Base,
    BaseWork,
    JobDescriptionAnalysis,
    JobDescriptionProfile,
    Resume,
)
from shared.types.jd_profile import (
    JD_PROFILE_SCHEMA_VERSION,
    CoreSelectionCriterion,
    JdProfileData,
    JdProfileExtractionResult,
    JdProfileRequirement,
    JobResponsibility,
)
from shared.types.messages import ConversationMessage
from shared.types.task import TaskType


class FakeStreamingClient:
    def __init__(self, responses: list[list[ApiStreamEvent]]) -> None:
        self.responses = responses
        self.requests: list[ApiMessageRequest] = []

    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        self.requests.append(request)
        response = self.responses[len(self.requests) - 1]
        for event in response:
            yield event


def _complete_message(text: str) -> ApiMessageCompleteEvent:
    return ApiMessageCompleteEvent(
        message=ConversationMessage.from_user_text(text).model_copy(
            update={"role": "assistant"}
        ),
        usage=UsageSnapshot(input_tokens=1, output_tokens=1),
    )


def test_jd_source_hash_normalizes_whitespace_and_tracks_title() -> None:
    first = calculate_jd_source_hash(" 熟练   Python\n开发 ", "算法实习生")
    second = calculate_jd_source_hash("熟练 Python 开发", " 算法实习生 ")
    different_title = calculate_jd_source_hash("熟练 Python 开发", "后端实习生")
    different_body = calculate_jd_source_hash("熟练 Python 与 RAG 开发", "算法实习生")

    assert first == second
    assert first != different_title
    assert first != different_body


def test_profile_completeness_rejects_dropped_selection_sections() -> None:
    profile = JdProfileExtractionResult(
        responsibilities=[
            {"name": "开发 LLM 应用"},
            {"name": "优化 Agent Workflow"},
        ]
    )
    jd = """\
## 工作职责
1. 负责 LLM 应用开发
2. 优化 Agent Workflow
## 什么样的人可能不太适合
只会调用框架，讲不清为什么做。
## 团队当前方向
建设 Memory 系统和面向用户的 AI 产品。
"""

    error = _validate_profile_completeness(profile, jd)

    assert error is not None
    assert "anti-fit" in error or "selection criteria" in error


def test_profile_completeness_allows_short_jd_without_marked_sections() -> None:
    error = _validate_profile_completeness(
        JdProfileExtractionResult(), "熟练使用 Python，参与后端开发。"
    )

    assert error is None


def test_profile_completeness_supports_english_section_aliases() -> None:
    profile = JdProfileExtractionResult(
        responsibilities=[{"name": "Build LLM applications"}, {"name": "Improve workflows"}],
        anti_fit_signals=[{"name": "Only invokes frameworks without explaining decisions"}],
    )
    jd = """\
# Responsibilities
Build LLM applications and improve workflows.
# Who is not a fit
Only invokes frameworks without explaining decisions.
# What we look for
Can connect technical decisions to user impact.
"""

    error = _validate_profile_completeness(profile, jd)

    assert error is not None
    assert "selection criteria" in error


def test_parse_jd_profile_adds_source_metadata() -> None:
    async def run_case() -> None:
        role_payload = {
            "roleProfile": {
                "roleFamily": "llm_application_algorithm",
                "seniority": "intern",
                "domain": ["Agent", "Memory"],
                "teamContext": ["Memory 系统"],
                "coreKeywords": ["Python", "RAG"],
            },
            "requirements": [
                {
                    "id": "req_python",
                    "name": "Python",
                    "category": "hard_skill",
                    "importance": "mandatory",
                    "level": "熟练",
                    "evidenceRequired": ["真实项目"],
                    "resumeEvidenceTypes": ["projects", "work_experience"],
                    "interviewProbeTopics": ["讲一个 Python 后端服务设计"],
                    "negativeSignals": ["只写会调用 API"],
                    "weight": 9,
                    "confidence": 0.95,
                }
            ],
        }
        responsibilities_payload = {
            "responsibilities": [],
        }
        signals_payload = {
            "evaluationRubric": [],
            "fitSignals": [],
            "antiFitSignals": [],
            "coreSelectionCriteria": [],
        }
        strategy_payload = {
            "resumeStrategy": {
                "emphasize": ["真实 LLM 项目"],
                "avoidClaims": ["未提供证据的技能"],
                "missingEvidenceToCollect": [],
                "rewriteGuidance": [],
            },
            "interviewStrategy": {
                "focusAreas": ["问题定位"],
                "probeQuestions": ["为什么这么设计？"],
                "riskChecks": ["是否只会调框架"],
            },
            "ambiguities": [],
        }
        payloads = [
            role_payload,
            responsibilities_payload,
            signals_payload,
            strategy_payload,
        ]
        client = FakeStreamingClient(
            [
                [
                    ApiTextDeltaEvent(text=json.dumps(payload, ensure_ascii=False)),
                    _complete_message(json.dumps(payload, ensure_ascii=False)),
                ]
                for payload in payloads
            ]
        )
        source_hash = calculate_jd_source_hash("熟练使用 Python", "算法实习生")

        result = await parse_jd_profile(
            client,
            "model",
            "熟练使用 Python",
            "算法实习生",
            source_hash,
        )

        assert result.source.job_title == "算法实习生"
        assert result.source.source_hash == source_hash
        assert result.source.language == "zh"
        assert result.requirements[0].id == "req_python"
        assert result.requirements[0].weight == 9
        assert len(client.requests) == 4
        assert "JdProfileRoleResult" in client.requests[0].system_prompt

    asyncio.run(run_case())


def test_profile_prompt_views_do_not_include_legacy_raw_text() -> None:
    profile = JdProfileData(
        requirements=[
            JdProfileRequirement(
                id="req-python",
                name="Python",
                category="hard_skill",
                importance="mandatory",
            )
        ],
        responsibilities=[
            JobResponsibility(
                name="开发服务",
                output_expectations=["稳定运行"],
            )
        ],
        core_selection_criteria=[
            CoreSelectionCriterion(
                id="criterion-python",
                criterion="具备 Python 开发能力",
            )
        ],
    )

    for view in ("greeting", "cover_letter", "interview", "resume"):
        formatted = format_jd_profile_for_prompt(profile, view)
        assert "raw_text" not in formatted
        assert "rawText" not in formatted

    resume_view = json.loads(format_jd_profile_for_prompt(profile, "resume"))
    assert resume_view["responsibilities"][0]["output_expectations"] == ["稳定运行"]


def test_old_profile_json_can_be_read_without_legacy_raw_text() -> None:
    profile = JobDescriptionProfile(
        id=1,
        resume_id="resume-1",
        source_hash="hash",
        schema_version=3,
        status="ready",
        attempts=0,
        profile_json=json.dumps(
            {
                "source": {
                    "raw_text": "熟练使用 Python",
                    "job_title": "后端工程师",
                }
            },
            ensure_ascii=False,
        ),
    )

    parsed = profile.to_pydantic().profile

    assert parsed is not None
    assert parsed.source.job_title == "后端工程师"


def test_old_analysis_requirements_can_be_read_without_legacy_raw_text() -> None:
    analysis = JobDescriptionAnalysis(
        id=1,
        resume_id="resume-1",
        job_description="熟练使用 Python",
        overall_score=80,
        ats_score=80,
        summary="summary",
        keyword_matches="[]",
        missing_keywords="[]",
        suggestions="[]",
        partial_matches="[]",
        skill_matches="[]",
        strengths="[]",
        jd_requirements=json.dumps(
            [
                {
                    "name": "Python",
                    "category": "hard_skill",
                    "importance": "mandatory",
                    "raw_text": "熟练使用 Python",
                }
            ],
            ensure_ascii=False,
        ),
    )

    parsed = analysis.to_pydantic()

    assert parsed.jd_requirements[0].name == "Python"


def test_stuck_queued_profile_without_work_is_rescheduled() -> None:
    async def run_case() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            resume_id = str(uuid.uuid4())
            resume = Resume(
                id=resume_id,
                workspace_id=str(uuid.uuid4()),
                title="sub",
                template="classic",
                theme_config="{}",
                language="zh",
                meta_info={"job_description": "熟练使用 Python", "job_title": "算法实习生"},
            )
            source_hash = calculate_jd_source_hash("熟练使用 Python", "算法实习生")
            profile = JobDescriptionProfile(
                resume_id=resume_id,
                source_hash=source_hash,
                schema_version=JD_PROFILE_SCHEMA_VERSION,
                status="queued",
            )
            session.add_all([resume, profile])
            await session.commit()

            result = await ensure_jd_profile(
                session,
                resume,
                trigger="manual_retry",
                background_tasks=BackgroundTasks(),
                provider_override=ProviderRuntimeConfig(
                    provider_type="openai",
                    api_key="test",
                    base_url="http://example.test",
                    model="model",
                ),
                mode="background",
                retry_failed=True,
            )

            assert result is not None
            assert result.status == "queued"
            assert result.provider_type == "openai"
            work = (
                await session.execute(
                    select(BaseWork).where(BaseWork.task_type == TaskType.JD_PARSE.value)
                )
            ).scalar_one()
            assert work.meta_info["resume_id"] == resume_id
            assert work.meta_info["source_hash"] == source_hash

        await engine.dispose()

    asyncio.run(run_case())
