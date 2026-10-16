from datetime import datetime
from typing import Literal

from pydantic import Field

from shared.types.strict_model import StrictBaseModel

JD_PROFILE_SCHEMA_VERSION = 4

JdProfileStatus = Literal[
    "pending_config",
    "queued",
    "running",
    "ready",
    "failed",
    "obsolete",
]

JdRequirementCategory = Literal[
    "hard_skill",
    "soft_skill",
    "tool",
    "domain_knowledge",
    "certification",
    "education",
    "experience",
    "language",
]

JdRequirementImportance = Literal["mandatory", "preferred", "bonus"]


class JdProfileSource(StrictBaseModel):
    job_title: str | None = Field(default=None, description="Target job title")
    source_hash: str = Field(default="", description="Stable hash of current JD source")
    language: str = Field(default="unknown", description="JD language")


class RoleProfile(StrictBaseModel):
    role_family: str = Field(default="", description="Role family inferred from JD")
    seniority: str = Field(default="", description="Seniority, e.g. intern/senior")
    domain: list[str] = Field(default_factory=list, description="Main work domains")
    team_context: list[str] = Field(
        default_factory=list, description="Team/business context"
    )
    core_keywords: list[str] = Field(
        default_factory=list, description="Core keywords in the JD"
    )


class JdProfileRequirement(StrictBaseModel):
    id: str = Field(default="", description="Stable semantic requirement id")
    name: str = Field(description="Requirement name")
    category: JdRequirementCategory = Field(description="Requirement category")
    importance: JdRequirementImportance = Field(description="Requirement importance")
    level: str | None = Field(default=None, description="Required proficiency or level")
    evidence_required: list[str] = Field(
        default_factory=list,
        description="Evidence expected in resume/interview",
    )
    resume_evidence_types: list[str] = Field(
        default_factory=list,
        description="Resume sections likely to prove this requirement",
    )
    interview_probe_topics: list[str] = Field(
        default_factory=list,
        description="Interview topics that verify this requirement",
    )
    negative_signals: list[str] = Field(
        default_factory=list,
        description="Signals that contradict this requirement",
    )
    weight: int = Field(default=5, ge=1, le=10, description="Importance weight")
    confidence: float = Field(
        default=0.8, ge=0, le=1, description="Extraction confidence"
    )


class JobResponsibility(StrictBaseModel):
    name: str = Field(description="Responsibility name")
    related_requirements: list[str] = Field(
        default_factory=list, description="Requirement ids related to this responsibility"
    )
    output_expectations: list[str] = Field(
        default_factory=list, description="Expected outputs or outcomes"
    )
    weight: int = Field(default=5, ge=1, le=10, description="Responsibility weight")


class EvaluationCriterion(StrictBaseModel):
    name: str = Field(description="How the employer evaluates candidates")
    positive_evidence: list[str] = Field(default_factory=list)
    negative_evidence: list[str] = Field(default_factory=list)
    interview_probe: str | None = Field(default=None)
    weight: int = Field(default=5, ge=1, le=10)


class FitSignal(StrictBaseModel):
    name: str = Field(description="Positive fit signal")
    resume_hint: str | None = Field(default=None)
    interview_probe: str | None = Field(default=None)
    weight: int = Field(default=5, ge=1, le=10)


class AntiFitSignal(StrictBaseModel):
    name: str = Field(description="Negative fit signal")
    severity: Literal["low", "medium", "high"] = Field(default="medium")
    resume_warning: str | None = Field(default=None)
    interview_probe: str | None = Field(default=None)


class CoreSelectionCriterion(StrictBaseModel):
    """招聘方真正用来筛选候选人的核心标准。"""

    id: str = Field(description="Stable semantic criterion id")
    criterion: str = Field(description="Positive selection criterion")
    priority: Literal["critical", "important", "bonus"] = "important"
    weight: int = Field(default=8, ge=1, le=10)
    source_section: str | None = Field(default=None, description="JD section name")
    negative_signals: list[str] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)
    resume_evidence_types: list[str] = Field(default_factory=list)
    product_implication: str | None = Field(default=None)


class ResumeStrategy(StrictBaseModel):
    emphasize: list[str] = Field(default_factory=list)
    avoid_claims: list[str] = Field(default_factory=list)
    missing_evidence_to_collect: list[str] = Field(default_factory=list)
    rewrite_guidance: list[str] = Field(default_factory=list)


class InterviewStrategy(StrictBaseModel):
    focus_areas: list[str] = Field(default_factory=list)
    probe_questions: list[str] = Field(default_factory=list)
    risk_checks: list[str] = Field(default_factory=list)


class JdProfileExtractionResult(StrictBaseModel):
    role_profile: RoleProfile = Field(default_factory=RoleProfile)
    requirements: list[JdProfileRequirement] = Field(default_factory=list)
    responsibilities: list[JobResponsibility] = Field(default_factory=list)
    evaluation_rubric: list[EvaluationCriterion] = Field(default_factory=list)
    fit_signals: list[FitSignal] = Field(default_factory=list)
    anti_fit_signals: list[AntiFitSignal] = Field(default_factory=list)
    core_selection_criteria: list[CoreSelectionCriterion] = Field(default_factory=list)
    resume_strategy: ResumeStrategy = Field(default_factory=ResumeStrategy)
    interview_strategy: InterviewStrategy = Field(default_factory=InterviewStrategy)
    ambiguities: list[str] = Field(default_factory=list)


class JdProfileRoleResult(StrictBaseModel):
    role_profile: RoleProfile = Field(default_factory=RoleProfile)
    requirements: list[JdProfileRequirement] = Field(default_factory=list)


class JdProfileResponsibilitiesResult(StrictBaseModel):
    responsibilities: list[JobResponsibility] = Field(default_factory=list)


class JdProfileSignalsResult(StrictBaseModel):
    evaluation_rubric: list[EvaluationCriterion] = Field(default_factory=list)
    fit_signals: list[FitSignal] = Field(default_factory=list)
    anti_fit_signals: list[AntiFitSignal] = Field(default_factory=list)
    core_selection_criteria: list[CoreSelectionCriterion] = Field(default_factory=list)


class JdProfileStrategyResult(StrictBaseModel):
    resume_strategy: ResumeStrategy = Field(default_factory=ResumeStrategy)
    interview_strategy: InterviewStrategy = Field(default_factory=InterviewStrategy)
    ambiguities: list[str] = Field(default_factory=list)


class JdProfileData(JdProfileExtractionResult):
    schema_version: int = Field(default=JD_PROFILE_SCHEMA_VERSION)
    source: JdProfileSource = Field(default_factory=JdProfileSource)


class JobDescriptionProfileSchema(StrictBaseModel):
    id: int = Field(description="Profile record id")
    resume_id: str = Field(description="Sub resume id")
    source_hash: str = Field(description="Hash of normalized JD source")
    schema_version: int = Field(default=JD_PROFILE_SCHEMA_VERSION)
    status: JdProfileStatus = Field(description="Profile parsing status")
    profile: JdProfileData | None = Field(default=None)
    error_message: str | None = Field(default=None)
    attempts: int = Field(default=0)
    provider_type: str | None = Field(default=None)
    model: str | None = Field(default=None)
    trigger: str | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)


class CurrentJdProfileResponse(StrictBaseModel):
    resume_id: str = Field(description="Sub resume id")
    source_hash: str | None = Field(default=None)
    has_job_description: bool = Field(default=False)
    profile: JobDescriptionProfileSchema | None = Field(default=None)
    needs_parse: bool = Field(default=False)
