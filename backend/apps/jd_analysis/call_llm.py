import asyncio
import json
import re
from collections.abc import Callable

from apps.jd_analysis.prompt import (
    EXTRACTION_SYSTEM,
    build_extraction_user_prompt,
    build_match_user_prompt,
    derive_requirements_summary,
)
from apps.jd_analysis.schemas import (
    JdExtractionResult,
    JdRequirementItem,
    KeywordMatchItem,
    KeywordMissingItem,
    MatchResult,
    PartialMatchItem,
    RequirementAssessment,
    RequirementAssessmentBatch,
    ScoringSummary,
    SkillMatchItem,
    SuggestionResult,
)
from chiren_backend.platform.llm import call_structured_json
from chiren_backend.platform.llm.client import SupportsStreamingMessages
from shared.types.jd_profile import JdProfileData
from shared.types.resume import ResumeSectionSchema

MAX_RETRIES = 3
REQUIREMENTS_PER_CHUNK = 5
MAX_ASSESSMENT_CONCURRENCY = 4
LLM_TASK_MAX_TOKENS = 16384


async def executor_llm(
    client: SupportsStreamingMessages,
    model: str,
    sections: list[ResumeSectionSchema],
    job_description: str,
    job_title: str | None = None,
    jd_profile: JdProfileData | None = None,
) -> tuple[MatchResult, JdExtractionResult]:
    """执行 JD 评分，保持 profile 解析与评分结果的边界。"""
    extraction = await _get_extraction(
        client, model, job_description, job_title, jd_profile
    )
    requirement_refs = _make_requirement_refs(extraction)
    requirements_content = derive_requirements_summary(extraction)
    assessments = await _assess_requirements(
        client,
        model,
        sections,
        job_description,
        job_title,
        requirement_refs,
    )
    summary_task = asyncio.create_task(
        _generate_scoring_summary(
            client,
            model,
            sections,
            job_description,
            job_title,
            requirements_content,
            requirement_refs,
            assessments,
        )
    )
    suggestions_task = asyncio.create_task(
        _generate_suggestions(
            client,
            model,
            sections,
            job_description,
            job_title,
            requirements_content,
            assessments,
        )
    )
    summary, suggestions = await asyncio.gather(summary_task, suggestions_task)

    return (
        _assemble_match_result(
            requirement_refs,
            assessments,
            summary,
            suggestions,
        ),
        extraction,
    )


async def _get_extraction(
    client: SupportsStreamingMessages,
    model: str,
    job_description: str,
    job_title: str | None,
    jd_profile: JdProfileData | None,
) -> JdExtractionResult:
    if jd_profile is not None:
        return _extraction_from_profile(jd_profile)

    extraction_system = EXTRACTION_SYSTEM.format(
        json_schema=json.dumps(
            JdExtractionResult.model_json_schema(),
            indent=2,
            ensure_ascii=False,
        )
    )
    return await call_structured_json(
        client,
        model,
        extraction_system,
        build_extraction_user_prompt(job_description, job_title),
        JdExtractionResult,
        max_retries=MAX_RETRIES,
        max_tokens=LLM_TASK_MAX_TOKENS,
        temperature=0.0,
    )


def _make_requirement_refs(
    extraction: JdExtractionResult,
) -> list[tuple[str, JdRequirementItem]]:
    counts: dict[str, int] = {}
    refs: list[tuple[str, JdRequirementItem]] = []
    for requirement in extraction.requirements:
        normalized_name = re.sub(r"\s+", " ", requirement.name.casefold()).strip()
        base_key = f"{requirement.category}:{normalized_name}"
        counts[base_key] = counts.get(base_key, 0) + 1
        suffix = counts[base_key]
        key = base_key if suffix == 1 else f"{base_key}#{suffix}"
        refs.append((key, requirement))
    return refs


async def _assess_requirements(
    client: SupportsStreamingMessages,
    model: str,
    sections: list[ResumeSectionSchema],
    job_description: str,
    job_title: str | None,
    requirement_refs: list[tuple[str, JdRequirementItem]],
) -> list[RequirementAssessment]:
    chunks = [
        requirement_refs[index : index + REQUIREMENTS_PER_CHUNK]
        for index in range(0, len(requirement_refs), REQUIREMENTS_PER_CHUNK)
    ]
    semaphore = asyncio.Semaphore(MAX_ASSESSMENT_CONCURRENCY)

    async def run_chunk(
        chunk: list[tuple[str, JdRequirementItem]],
    ) -> list[RequirementAssessment]:
        async with semaphore:
            expected_keys = {key for key, _ in chunk}
            requirements = [
                {"requirementKey": key, **requirement.model_dump(mode="json")}
                for key, requirement in chunk
            ]
            system_prompt = _assessment_system_prompt()
            user_prompt = _assessment_user_prompt(
                sections,
                job_description,
                job_title,
                requirements,
            )
            result = await call_structured_json(
                client,
                model,
                system_prompt,
                user_prompt,
                RequirementAssessmentBatch,
                max_retries=MAX_RETRIES,
                max_tokens=LLM_TASK_MAX_TOKENS,
                temperature=0.0,
                post_validator=_make_assessment_validator(expected_keys),
            )
            return result.assessments

    tasks = [asyncio.create_task(run_chunk(chunk)) for chunk in chunks]
    batches = await asyncio.gather(*tasks)
    return [assessment for batch in batches for assessment in batch]


def _assessment_system_prompt() -> str:
    schema = json.dumps(
        RequirementAssessmentBatch.model_json_schema(), indent=2, ensure_ascii=False
    )
    return f"""\
You evaluate a small set of job requirements against a resume.

Return ONLY one JSON object matching this schema:
<json_schema>
{schema}
</json_schema>

Rules:
- Return exactly one assessment for every supplied requirementKey.
- Never invent a requirementKey.
- matched means sufficient evidence exists; partial means related evidence exists but
  the required level or depth is not met; missing means no reliable evidence exists.
- Use match_type=none for missing requirements.
- Keep evidence and gap descriptions concise.
"""


def _assessment_user_prompt(
    sections: list[ResumeSectionSchema],
    job_description: str,
    job_title: str | None,
    requirements: list[dict[str, object]],
) -> str:
    requirements_json = json.dumps(requirements, ensure_ascii=False, indent=2)
    return (
        f"<requirements_to_assess>\n{requirements_json}\n</requirements_to_assess>\n\n"
        + build_match_user_prompt(sections, job_description, job_title)
    )


def _make_assessment_validator(
    expected_keys: set[str],
) -> Callable[[RequirementAssessmentBatch], str | None]:
    def validator(result: RequirementAssessmentBatch) -> str | None:
        actual_keys = [assessment.requirement_key for assessment in result.assessments]
        actual_set = set(actual_keys)
        if len(actual_keys) != len(actual_set):
            return "Validation failed: duplicate requirementKey values were returned."
        if actual_set != expected_keys:
            return (
                "Validation failed: requirementKey coverage mismatch. "
                f"missing={sorted(expected_keys - actual_set)}, "
                f"unexpected={sorted(actual_set - expected_keys)}"
            )
        return None

    return validator


async def _generate_scoring_summary(
    client: SupportsStreamingMessages,
    model: str,
    sections: list[ResumeSectionSchema],
    job_description: str,
    job_title: str | None,
    requirements_content: str,
    requirement_refs: list[tuple[str, JdRequirementItem]],
    assessments: list[RequirementAssessment],
) -> ScoringSummary:
    schema = json.dumps(
        ScoringSummary.model_json_schema(), indent=2, ensure_ascii=False
    )
    system_prompt = f"""\
You summarize a resume's fit for a job from authoritative requirement assessments.
Return ONLY one JSON object matching this schema:
<json_schema>
{schema}
</json_schema>

Scores must be integers from 0 to 100. Do not invent resume evidence.
"""
    user_prompt = _analysis_context_prompt(
        sections,
        job_description,
        job_title,
        requirements_content,
        requirement_refs,
        assessments,
    )
    return await call_structured_json(
        client,
        model,
        system_prompt,
        user_prompt,
        ScoringSummary,
        max_retries=MAX_RETRIES,
        max_tokens=LLM_TASK_MAX_TOKENS,
        temperature=0.0,
    )


async def _generate_suggestions(
    client: SupportsStreamingMessages,
    model: str,
    sections: list[ResumeSectionSchema],
    job_description: str,
    job_title: str | None,
    requirements_content: str,
    assessments: list[RequirementAssessment],
) -> SuggestionResult:
    schema = json.dumps(
        SuggestionResult.model_json_schema(), indent=2, ensure_ascii=False
    )
    system_prompt = f"""\
You generate concise, actionable resume suggestions from an existing JD assessment.
Return ONLY one JSON object matching this schema:
<json_schema>
{schema}
</json_schema>

Rules:
- Return at most 10 suggestions.
- Use only the supplied resume section IDs.
- Never invent candidate experience or achievements.
- Keep current and suggested text concise.
"""
    assessment_json = json.dumps(
        [assessment.model_dump(mode="json") for assessment in assessments],
        ensure_ascii=False,
        indent=2,
    )
    user_prompt = (
        f"<requirements>\n{requirements_content}\n</requirements>\n"
        f"<assessments>\n{assessment_json}\n</assessments>\n"
        "\n"
        + build_match_user_prompt(sections, job_description, job_title)
    )
    return await call_structured_json(
        client,
        model,
        system_prompt,
        user_prompt,
        SuggestionResult,
        max_retries=MAX_RETRIES,
        max_tokens=LLM_TASK_MAX_TOKENS,
        temperature=0.0,
        post_validator=_make_suggestion_validator(sections),
    )


def _analysis_context_prompt(
    sections: list[ResumeSectionSchema],
    job_description: str,
    job_title: str | None,
    requirements_content: str,
    requirement_refs: list[tuple[str, JdRequirementItem]],
    assessments: list[RequirementAssessment],
) -> str:
    requirements = [
        {"requirementKey": key, **requirement.model_dump(mode="json")}
        for key, requirement in requirement_refs
    ]
    assessments_json = json.dumps(
        [assessment.model_dump(mode="json") for assessment in assessments],
        ensure_ascii=False,
        indent=2,
    )
    requirements_json = json.dumps(requirements, ensure_ascii=False, indent=2)
    return (
        f"<requirements_summary>\n{requirements_content}\n</requirements_summary>\n"
        f"<requirements>\n{requirements_json}\n</requirements>\n"
        f"<assessments>\n{assessments_json}\n</assessments>\n\n"
        + build_match_user_prompt(sections, job_description, job_title)
    )


def _make_suggestion_validator(
    sections: list[ResumeSectionSchema],
) -> Callable[[SuggestionResult], str | None]:
    valid_section_ids = {section.id for section in sections}

    def validator(result: SuggestionResult) -> str | None:
        invalid_ids = [
            suggestion.section_id
            for suggestion in result.suggestions
            if suggestion.section_id not in valid_section_ids
        ]
        if invalid_ids:
            return (
                "Validation failed: invalid sectionId values "
                f"{invalid_ids}; valid values are {sorted(valid_section_ids)}"
            )
        if len(result.suggestions) > 10:
            return "Validation failed: suggestions must contain at most 10 items."
        return None

    return validator


def _assemble_match_result(
    requirement_refs: list[tuple[str, JdRequirementItem]],
    assessments: list[RequirementAssessment],
    summary: ScoringSummary,
    suggestions: SuggestionResult,
) -> MatchResult:
    assessments_by_key = {
        assessment.requirement_key: assessment for assessment in assessments
    }
    keyword_matches: list[KeywordMatchItem] = []
    missing_keywords: list[KeywordMissingItem] = []
    partial_matches: list[PartialMatchItem] = []
    skill_matches: list[SkillMatchItem] = []

    for key, requirement in requirement_refs:
        assessment = assessments_by_key[key]
        importance = _importance_score(requirement.importance)
        category = _keyword_category(requirement.importance)
        if assessment.status == "matched":
            keyword_matches.append(
                KeywordMatchItem(
                    keyword=requirement.name,
                    category=category,
                    importance=importance,
                    match_type=(
                        assessment.match_type
                        if assessment.match_type != "none"
                        else "contextual"
                    ),
                    evidence=assessment.evidence,
                )
            )
        elif assessment.status == "missing":
            missing_keywords.append(
                KeywordMissingItem(
                    keyword=requirement.name,
                    category=category,
                    importance=importance,
                )
            )
        else:
            partial_matches.append(
                PartialMatchItem(
                    keyword=requirement.name,
                    resume_level=assessment.resume_level or "Not clearly specified",
                    job_level=requirement.level or "Not specified",
                    gap_description=assessment.gap_description
                    or "The resume evidence does not fully meet the requirement.",
                )
            )

        skill_category = _skill_category(requirement.category)
        if skill_category is not None:
            skill_matches.append(
                SkillMatchItem(
                    skill=requirement.name,
                    match_score=assessment.match_score,
                    category=skill_category,
                )
            )

    return MatchResult(
        summary=summary.summary,
        overall_score=summary.overall_score,
        ats_score=summary.ats_score,
        keyword_matches=keyword_matches,
        missing_keywords=missing_keywords,
        suggestions=suggestions.suggestions,
        partial_matches=partial_matches,
        skill_matches=skill_matches,
        strengths=summary.strengths,
    )


def _importance_score(importance: str) -> int:
    return {"mandatory": 10, "preferred": 6, "bonus": 3}[importance]


def _keyword_category(importance: str) -> str:
    return {"mandatory": "required", "preferred": "preferred", "bonus": "bonus"}[
        importance
    ]


def _skill_category(category: str) -> str | None:
    return {
        "hard_skill": "technical",
        "soft_skill": "soft_skill",
        "tool": "tool",
        "domain_knowledge": "domain",
        "certification": "certification",
    }.get(category)


def _extraction_from_profile(jd_profile: JdProfileData) -> JdExtractionResult:
    return JdExtractionResult(
        requirements=[
            {
                "name": req.name,
                "category": req.category,
                "importance": req.importance,
                "level": req.level,
            }
            for req in jd_profile.requirements
        ]
    )
