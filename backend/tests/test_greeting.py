"""招呼语结构化结果与事实证据校验测试。"""

import json

import pytest

from apps.greeting.prompt import build_system_prompt, build_user_prompt
from apps.greeting.service import _validate_evidence
from apps.jd_profile.formatting import format_jd_profile_for_prompt
from chiren_backend.platform.models import ResumeSection
from shared.types.greeting import GreetingGenerationResult, GreetingMatchPoint
from shared.types.jd_profile import (
    CoreSelectionCriterion,
    FitSignal,
    JdProfileData,
    JdProfileRequirement,
    JobResponsibility,
)


def _result(evidence: str = "负责 Python 服务开发") -> GreetingGenerationResult:
    return GreetingGenerationResult.model_validate(
        {
            "variants": [
                {"style": "professional", "text": "您好，我有相关项目经验，希望进一步沟通。", "matchPoints": [{"requirementId": "python", "evidence": evidence}]},
                {"style": "natural", "text": "您好，看到岗位后觉得经历比较匹配，想和您聊聊。", "matchPoints": [{"requirementId": "python", "evidence": evidence}]},
                {"style": "match_focused", "text": "您好，我做过 Python 服务开发，和岗位方向有直接结合。", "matchPoints": [{"requirementId": "python", "evidence": evidence}]},
            ]
        }
    )


def _profile() -> JdProfileData:
    return JdProfileData(
        requirements=[
            JdProfileRequirement(
                id="python",
                name="Python",
                category="hard_skill",
                importance="mandatory",
            )
        ]
    )


def test_greeting_result_requires_three_unique_styles() -> None:
    result = _result()
    assert {variant.style for variant in result.variants} == {
        "professional",
        "natural",
        "match_focused",
    }


def test_greeting_text_has_no_artificial_maximum_length() -> None:
    payload = _result().model_dump(by_alias=True)
    payload["variants"][0]["text"] = "您好，" + "这是一段较长但仍然完整的岗位匹配说明。" * 30

    result = GreetingGenerationResult.model_validate(payload)

    assert len(result.variants[0].text) > 180


def test_greeting_evidence_may_be_a_natural_resume_paraphrase() -> None:
    section = ResumeSection(
        id="section-1",
        resume_id="resume-1",
        title="项目经历",
        type="projects",
        content='{"items":[{"description":"负责 Python 服务开发"}]}',
    )
    assert _validate_evidence(_result(), _profile()) is None
    assert _validate_evidence(_result("没有这段经历"), _profile()) is None


def test_greeting_rejects_core_criterion_id_in_requirement_point() -> None:
    profile = _profile().model_copy(
        update={
            "core_selection_criteria": [
                CoreSelectionCriterion(
                    id="memory_system_design",
                    criterion="Design memory systems",
                )
            ]
        }
    )
    invalid_result = _result().model_copy(
        update={
            "variants": [
                variant.model_copy(
                    update={
                        "match_points": [
                            GreetingMatchPoint(
                                requirement_id="memory_system_design",
                                evidence="负责 Python 服务开发",
                            )
                        ],
                        "selection_criterion_id": "memory_system_design",
                    }
                )
                for variant in _result().variants
            ]
        }
    )

    error = _validate_evidence(invalid_result, profile)

    assert error is not None
    assert "requirements[].id" in error


def test_greeting_result_rejects_duplicate_styles() -> None:
    payload = _result().model_dump(by_alias=True)
    payload["variants"][1]["style"] = "professional"
    with pytest.raises(ValueError, match="unique styles"):
        GreetingGenerationResult.model_validate(payload)


def test_greeting_prompt_contains_raw_jd_and_structured_profile() -> None:
    prompt = build_user_prompt(
        "算法实习生",
        "负责推荐系统特征工程，并与业务团队协作推进实验。",
        "<jd_profile>structured profile</jd_profile>",
        "<resume_sections>resume</resume_sections>",
    )
    assert "<raw_job_description>" in prompt
    assert "负责推荐系统特征工程" in prompt
    assert "<jd_profile>structured profile</jd_profile>" in prompt
    system_prompt = build_system_prompt()
    assert "strongest JD-to-resume matches" in system_prompt
    assert "whole resume evidence pool" in system_prompt
    assert "summary, skills, education, work experience, projects" in system_prompt
    assert "Do not stop at" in system_prompt
    assert "Scanning the whole resume is for discovery, not for inclusion" in system_prompt
    assert "unrelated to this JD" in system_prompt
    assert "distribute the variants across" in system_prompt
    assert "one main match" in system_prompt
    assert "do not force diversity" in system_prompt
    assert "Every match point must support" in system_prompt
    assert "roughly 60-110" in system_prompt
    assert "Optional bonuses may be included" in system_prompt
    assert "Examples are for writing style only" in system_prompt
    assert "exactly three unique variants" in system_prompt
    assert "GitHub" not in system_prompt
    assert "Claude Code" not in system_prompt


def test_greeting_profile_projection_contains_role_context_and_bonus_signals() -> None:
    profile = _profile().model_copy(
        update={
            "responsibilities": [
                JobResponsibility(
                    name="配置 AI Skills 和 MCP 工具", output_expectations=["完成集成"]
                )
            ],
            "fit_signals": [
                FitSignal(name="独立 Agent 项目", resume_hint="GitHub 项目链接")
            ],
        }
    )

    projected = json.loads(format_jd_profile_for_prompt(profile, "greeting"))

    assert projected["responsibilities"][0]["name"] == "配置 AI Skills 和 MCP 工具"
    assert projected["fit_signals"][0]["resume_hint"] == "GitHub 项目链接"
    assert "role_profile" in projected
