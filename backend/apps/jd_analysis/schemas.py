from typing import Literal

from pydantic import Field

from shared.types.strict_model import StrictBaseModel


class MatchRequest(StrictBaseModel):
    resume_id: str = Field(description="简历id")
    type: Literal["openai", "anthropic"] = Field(description="LLM 供应商类型")
    base_url: str = Field(description="AI API 地址")
    api_key: str = Field(description="AI API 密钥")
    model: str = Field(description="模型名称")


class JdRequirementItem(StrictBaseModel):
    """A single requirement extracted from the JD by LLM (Phase A output)."""

    name: str = Field(
        description=(
            "Concise requirement name. "
            "e.g. 'Python', 'Docker', '3+ years backend experience', "
            "'Bachelor degree or above', 'Fluent English'"
        ),
    )
    category: Literal[
        "hard_skill",
        "soft_skill",
        "tool",
        "domain_knowledge",
        "certification",
        "education",
        "experience",
        "language",
    ] = Field(
        description=(
            "Requirement category: "
            "hard_skill=technical skill/stack (e.g. Python, React, SQL), "
            "soft_skill=soft skill (e.g. communication, teamwork), "
            "tool=tool/platform (e.g. Git, Docker, Figma), "
            "domain_knowledge=domain expertise (e.g. financial risk, healthcare compliance), "
            "certification=certificate/credential (e.g. PMP, AWS Certified), "
            "education=education level (e.g. Bachelor, Master), "
            "experience=work experience (e.g. 3+ years, 5+ years), "
            "language=language proficiency (e.g. Fluent English, JLPT N1)"
        ),
    )
    importance: Literal["mandatory", "preferred", "bonus"] = Field(
        description=(
            "Importance level: "
            "mandatory=deal-breaker requirement (JD uses 'must have', 'required', '须具备'), "
            "preferred=important but not critical (JD uses 'preferred', 'nice to have', '优先'), "
            "bonus=nice-to-have addition (JD uses 'bonus', '加分项', 'a plus')"
        ),
    )
    level: str | None = Field(
        default=None,
        description=(
            "Proficiency/level as stated in the JD, preserving original granularity. "
            "e.g. 'proficient', 'familiar', '3+ years', 'Bachelor or above'"
        ),
    )


class JdExtractionResult(StrictBaseModel):
    """Phase A LLM output: structured requirements extracted from a JD."""

    requirements: list[JdRequirementItem] = Field(
        description="Complete list of requirements extracted from the job description",
    )


class SuggestionItem(StrictBaseModel):
    section_id: str = Field(description="Unique section identifier in the resume")
    current: str = Field(description="Current content/text of the section")
    suggested: str = Field(description="Suggested improved content for the section")
    priority: Literal["high", "medium", "low"] = Field(
        description="Priority of this suggestion for the user"
    )
    type: Literal["content_gap", "wording", "keyword_add", "format", "structure"] = (
        Field(
            description=(
                "Suggestion type: "
                "content_gap=missing content (e.g. absent experience section), "
                "wording=phrasing improvement (e.g. 'responsible for' → 'led'), "
                "keyword_add=keyword addition (e.g. add 'Kubernetes'), "
                "format=formatting improvement (e.g. bullet points, quantification), "
                "structure=structural adjustment (e.g. reorder sections)"
            ),
        )
    )
    rationale: str = Field(description="Reason why this suggestion improves the resume")
    target_dimension: str | None = Field(
        default=None, description="Primary scoring dimension this suggestion affects"
    )
    expected_score_delta: int | None = Field(
        default=None,
        description="Estimated score improvement after applying this suggestion",
        ge=0,
        le=100,
    )


class PartialMatchItem(StrictBaseModel):
    keyword: str = Field(description="Keyword or requirement name")
    resume_level: str = Field(
        description="Actual description/level found in the resume"
    )
    job_level: str = Field(
        description="Required level as stated in the job description"
    )
    gap_description: str = Field(
        description="Explanation of the gap between resume level and job requirement"
    )


class SkillMatchItem(StrictBaseModel):
    skill: str = Field(description="Skill name")
    match_score: int = Field(description="Match score (0-100)", ge=0, le=100)
    category: Literal["technical", "domain", "tool", "soft_skill", "certification"] = (
        Field(
            description=(
                "Skill category: "
                "technical=tech stack (e.g. Python, React), "
                "domain=domain knowledge (e.g. finance, healthcare), "
                "tool=tools (e.g. Git, Docker), "
                "soft_skill=soft skills (e.g. communication, leadership), "
                "certification=certifications (e.g. PMP, AWS)"
            ),
        )
    )


class StrengthItem(StrictBaseModel):
    description: str = Field(description="Description of the core strength")
    type: Literal[
        "skill_match",
        "experience_match",
        "project_relevance",
        "certification",
        "education_match",
        "unique_advantage",
    ] = Field(
        description=(
            "Strength type: "
            "skill_match=high skill alignment, "
            "experience_match=high experience alignment, "
            "project_relevance=strong project relevance, "
            "certification=certification or credential match, "
            "education_match=education background match, "
            "unique_advantage=unique competitive advantage"
        ),
    )


class KeywordMatchItem(StrictBaseModel):
    keyword: str = Field(description="Matched keyword or requirement name")
    category: Literal["required", "preferred", "bonus"] = Field(
        description=(
            "Requirement type: "
            "required=must-have skill, "
            "preferred=nice-to-have skill, "
            "bonus=bonus/extracurricular skill"
        ),
    )
    importance: int = Field(description="Importance weight (1-10)", ge=1, le=10)
    match_type: Literal["exact", "synonym", "contextual"] = Field(
        description=(
            "Match type: "
            "exact=exact keyword match, "
            "synonym=synonym match (different wording, same concept), "
            "contextual=contextual match (implied by context but not explicitly stated)"
        ),
    )
    evidence: str | None = Field(
        default=None, description="Evidence or location of the match in the resume"
    )


class KeywordMissingItem(StrictBaseModel):
    keyword: str = Field(description="Missing keyword or requirement name")
    category: Literal["required", "preferred", "bonus"] = Field(
        description=(
            "Requirement type: "
            "required=must-have skill, "
            "preferred=nice-to-have skill, "
            "bonus=bonus/extracurricular skill"
        ),
    )
    importance: int = Field(description="Importance weight (1-10)", ge=1, le=10)
    suggestion: str | None = Field(
        default=None,
        description="Suggested improvement to address this missing keyword",
    )


class MatchResult(StrictBaseModel):
    summary: str = Field(
        description="Overall analysis summary of how well the resume matches the job"
    )
    overall_score: int = Field(
        description="Overall match score (0-100) across skills, experience, and keywords",
        ge=0,
        le=100,
    )
    ats_score: int = Field(
        description="ATS compatibility score (0-100): how well the resume can be parsed by applicant tracking systems",
        ge=0,
        le=100,
    )
    keyword_matches: list[KeywordMatchItem] = Field(
        default_factory=list,
        description="Keywords from the job description found in the resume, with match type and evidence",
    )
    missing_keywords: list[KeywordMissingItem] = Field(
        default_factory=list,
        description="Keywords required by the job but absent from the resume, categorized by importance",
    )
    suggestions: list[SuggestionItem] = Field(
        default_factory=list,
        description="Actionable suggestions for improving each resume section, with priority and expected score delta",
    )
    partial_matches: list[PartialMatchItem] = Field(
        default_factory=list,
        description="Partially met requirements where the resume mentions the topic but at insufficient depth",
    )
    skill_matches: list[SkillMatchItem] = Field(
        default_factory=list,
        description="Key skill match scores categorized by tech stack, domain, tools, etc.",
    )
    strengths: list[StrengthItem] = Field(
        default_factory=list,
        description="Core strengths of the resume that differentiate the candidate from others",
    )


class RequirementAssessment(StrictBaseModel):
    """单条 JD 要求的局部匹配评估。"""

    requirement_key: str = Field(description="Stable key assigned by the application")
    status: Literal["matched", "partial", "missing"]
    match_type: Literal["exact", "synonym", "contextual", "none"] = "none"
    match_score: int = Field(ge=0, le=100)
    evidence: str | None = None
    resume_level: str | None = None
    gap_description: str | None = None


class RequirementAssessmentBatch(StrictBaseModel):
    """一组 JD 要求的局部匹配评估。"""

    assessments: list[RequirementAssessment] = Field(default_factory=list)


class ScoringSummary(StrictBaseModel):
    """基于所有局部评估生成的紧凑评分总结。"""

    summary: str
    overall_score: int = Field(ge=0, le=100)
    ats_score: int = Field(ge=0, le=100)
    strengths: list[StrengthItem] = Field(default_factory=list)


class SuggestionResult(StrictBaseModel):
    """JD 评分后的简历修改建议。"""

    suggestions: list[SuggestionItem] = Field(default_factory=list)
