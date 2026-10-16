"""JD 评分中间结果与缓存 profile 行为测试。"""

import asyncio
from collections.abc import AsyncIterator

from apps.jd_analysis.call_llm import (
    _assemble_match_result,
    _get_extraction,
    _make_requirement_refs,
)
from apps.jd_analysis.schemas import (
    JdExtractionResult,
    RequirementAssessment,
    ScoringSummary,
    SuggestionResult,
)
from chiren_backend.platform.llm.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiStreamEvent,
)
from chiren_backend.platform.llm.usage import UsageSnapshot
from shared.types.jd_profile import JdProfileData, JdProfileRequirement
from shared.types.messages import ConversationMessage


class NoCallClient:
    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        raise AssertionError(f"unexpected model call: {request}")
        yield ApiMessageCompleteEvent(
            message=ConversationMessage.from_user_text(""),
            usage=UsageSnapshot(input_tokens=0, output_tokens=0),
        )


def test_cached_profile_bypasses_extraction_call() -> None:
    async def run_case() -> None:
        profile = JdProfileData(
            requirements=[
                JdProfileRequirement(
                    id="req-python",
                    name="Python",
                    category="hard_skill",
                    importance="mandatory",
                )
            ]
        )

        result = await _get_extraction(
            NoCallClient(),
            "model",
            "熟练使用 Python",
            "后端工程师",
            profile,
        )

        assert result.requirements[0].name == "Python"

    asyncio.run(run_case())


def test_assessments_are_merged_into_existing_match_contract() -> None:
    extraction = JdExtractionResult(
        requirements=[
            {
                "name": "Python",
                "category": "hard_skill",
                "importance": "mandatory",
                "level": "熟练",
            },
            {
                "name": "沟通",
                "category": "soft_skill",
                "importance": "preferred",
            },
        ]
    )
    refs = _make_requirement_refs(extraction)
    assessments = [
        RequirementAssessment(
            requirement_key=refs[0][0],
            status="matched",
            match_type="exact",
            match_score=95,
            evidence="项目中使用 Python 开发服务",
        ),
        RequirementAssessment(
            requirement_key=refs[1][0],
            status="partial",
            match_type="contextual",
            match_score=45,
            resume_level="参与跨团队协作",
            gap_description="缺少明确的沟通成果证据",
        ),
    ]
    result = _assemble_match_result(
        refs,
        assessments,
        ScoringSummary(
            summary="整体匹配较好",
            overall_score=78,
            ats_score=82,
        ),
        SuggestionResult(),
    )

    assert result.overall_score == 78
    assert result.keyword_matches[0].keyword == "Python"
    assert result.partial_matches[0].keyword == "沟通"
    assert result.skill_matches[0].category == "technical"
    assert result.skill_matches[1].category == "soft_skill"
