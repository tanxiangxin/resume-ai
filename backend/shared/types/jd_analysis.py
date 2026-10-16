from datetime import datetime
from typing import Literal

from pydantic import Field

from shared.types.strict_model import StrictBaseModel


class JdRequirementItem(StrictBaseModel):
    """LLM 从 JD 中提取的单个要求项。"""

    name: str = Field(
        description=(
            "要求名称，如 'Python', 'Docker', '3年以上后端开发经验', "
            "'本科及以上学历', '英语流利'"
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
            "要求类别: "
            "hard_skill=硬技能/技术栈 (如 Python, React, SQL), "
            "soft_skill=软技能 (如 沟通, 团队协作), "
            "tool=工具/平台 (如 Git, Docker, Figma), "
            "domain_knowledge=领域知识 (如 金融风控, 医疗合规), "
            "certification=证书/资质 (如 PMP, AWS认证), "
            "education=学历要求 (如 本科, 硕士), "
            "experience=工作经验 (如 3年+, 5年+), "
            "language=语言能力 (如 英语流利, 日语N1)"
        ),
    )
    importance: Literal["mandatory", "preferred", "bonus"] = Field(
        description=(
            "重要性: "
            "mandatory=硬性要求 (JD 中 '必须', '须具备', '要求'), "
            "preferred=优先要求 (JD 中 '优先', '熟悉', '加分'), "
            "bonus=锦上添花 (JD 中 '加分项', '更好', '如有')"
        ),
    )
    level: str | None = Field(
        default=None,
        description=(
            "要求的熟练度/级别，如 '精通', '熟练', '了解', '3年+', '本科及以上'"
        ),
    )


class SuggestionItem(StrictBaseModel):
    section_id: str = Field(description="简历中的唯一章节标识符")
    current: str = Field(description="当前章节的内容/文本")
    suggested: str = Field(description="建议改进后的章节内容")
    priority: Literal["high", "medium", "low"] = Field(
        description="该建议对用户的优先级"
    )
    type: Literal["content_gap", "wording", "keyword_add", "format", "structure"] = (
        Field(
            description=(
                "建议类型: "
                "content_gap=内容缺失 (例如缺少经验部分), "
                "wording=措辞改进 (例如 '负责' → '主导'), "
                "keyword_add=关键词补充 (例如添加 'Kubernetes'), "
                "format=格式改进 (例如项目符号、量化), "
                "structure=结构调整 (例如重新排序章节)"
            ),
        )
    )
    rationale: str = Field(description="该建议能改进简历的原因")
    target_dimension: str | None = Field(
        default=None, description="该建议主要影响的评分维度"
    )
    expected_score_delta: int | None = Field(
        default=None,
        description="应用该建议后预计的分数提升",
        ge=0,
        le=100,
    )


class PartialMatchItem(StrictBaseModel):
    keyword: str = Field(description="关键词或要求名称")
    resume_level: str = Field(description="简历中实际描述/达到的水平")
    job_level: str = Field(description="职位描述中要求的水平")
    gap_description: str = Field(description="简历水平与职位要求之间差距的说明")


class SkillMatchItem(StrictBaseModel):
    skill: str = Field(description="技能名称")
    match_score: int = Field(description="匹配分数 (0-100)", ge=0, le=100)
    category: Literal["technical", "domain", "tool", "soft_skill", "certification"] = (
        Field(
            description=(
                "技能类别: "
                "technical=技术栈 (例如 Python, React), "
                "domain=领域知识 (例如金融、医疗), "
                "tool=工具 (例如 Git, Docker), "
                "soft_skill=软技能 (例如沟通、领导力), "
                "certification=认证 (例如 PMP, AWS)"
            ),
        )
    )


class StrengthItem(StrictBaseModel):
    description: str = Field(description="核心优势的描述")
    type: Literal[
        "skill_match",
        "experience_match",
        "project_relevance",
        "certification",
        "education_match",
        "unique_advantage",
    ] = Field(
        description=(
            "优势类型: "
            "skill_match=高技能匹配度, "
            "experience_match=高经验匹配度, "
            "project_relevance=强项目相关性, "
            "certification=认证或资质匹配, "
            "education_match=教育背景匹配, "
            "unique_advantage=独特竞争优势"
        ),
    )


class KeywordMatchItem(StrictBaseModel):
    keyword: str = Field(description="匹配的关键词或要求名称")
    category: Literal["required", "preferred", "bonus"] = Field(
        description=(
            "要求类型: required=必需技能, preferred=加分技能, bonus=额外/附加技能"
        ),
    )
    importance: int = Field(description="重要性权重 (1-10)", ge=1, le=10)
    match_type: Literal["exact", "synonym", "contextual"] = Field(
        description=(
            "匹配类型: "
            "exact=精确关键词匹配, "
            "synonym=同义词匹配 (不同措辞，相同概念), "
            "contextual=上下文匹配 (由上下文暗示但未明确说明)"
        ),
    )
    evidence: str | None = Field(default=None, description="简历中匹配的证据或位置")


class KeywordMissingItem(StrictBaseModel):
    keyword: str = Field(description="缺失的关键词或要求名称")
    category: Literal["required", "preferred", "bonus"] = Field(
        description=(
            "要求类型: required=必需技能, preferred=加分技能, bonus=额外/附加技能"
        ),
    )
    importance: int = Field(description="重要性权重 (1-10)", ge=1, le=10)
    suggestion: str | None = Field(
        default=None,
        description="针对该缺失关键词的改进建议",
    )


class JobDescriptionAnalysisSchema(StrictBaseModel):
    id: int = Field(description="职位描述分析唯一标识")
    resume_id: str = Field(description="职位描述分析所属简历 ID")
    job_description: str = Field(description="职位描述")
    overall_score: int = Field(
        description="职位描述分析总分(0-100)",
        ge=0,
        le=100,
    )
    ats_score: int = Field(
        description="职位描述分析ATS得分(0-100)",
        ge=0,
        le=100,
    )
    summary: str = Field(description="职位描述分析总结")
    keyword_matches: list[KeywordMatchItem] = Field(
        default_factory=list,
        description="在简历中找到的职位关键词，包含匹配类型和证据",
    )
    missing_keywords: list[KeywordMissingItem] = Field(
        default_factory=list,
        description="职位要求但简历中缺失的关键词，按重要性分类",
    )
    suggestions: list[SuggestionItem] = Field(
        default_factory=list,
        description="针对每个简历部分的可操作改进建议，包含优先级和预计分数提升",
    )
    partial_matches: list[PartialMatchItem] = Field(
        default_factory=list,
        description="部分满足的要求，即简历提到该主题但深度不足",
    )
    skill_matches: list[SkillMatchItem] = Field(
        default_factory=list,
        description="按技术栈、领域、工具等分类的关键技能匹配分数",
    )
    strengths: list[StrengthItem] = Field(
        default_factory=list,
        description="简历的核心优势，体现候选人与他人的差异化",
    )
    jd_requirements: list[JdRequirementItem] = Field(
        default_factory=list,
        description="JD预提取结构化要求列表",
    )
    created_at: datetime | None = Field(default=None, description="创建时间")
