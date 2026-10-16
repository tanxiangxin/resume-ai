from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, alias_generators

from shared.types.mixins import NoneToDefaultMixin
from shared.types.strict_model import StrictBaseModel


class ResumeAssistantRequest(BaseModel):
    """请求参数"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    resume_id: str = Field(description="简历ID")
    type: Literal["openai", "anthropic"] = Field(description="LLM 供应商类型")
    base_url: str = Field(description="AI API 地址")
    api_key: str = Field(description="AI API 密钥")
    model: str = Field(description="模型名称")
    input: str = Field(description="用户输入")


class SubResumeCreateRequest(BaseModel):
    """根据 JD 创建子简历请求"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    workspace_id: str = Field(description="主简历/工作区 ID")
    job_description: str = Field(description="职位描述（JD）")
    job_title: str | None = Field(default=None, description="岗位名称")
    template: str = Field(default="classic", description="模板名称")
    title: str = Field(default="未命名简历", description="子简历标题")
    theme_config: dict = Field(default_factory=dict, description="主题配置")
    language: str = Field(default="zh", description="简历语言")
    type: Literal["openai", "anthropic"] = Field(description="LLM 供应商类型")
    base_url: str = Field(description="AI API 地址")
    api_key: str = Field(description="AI API 密钥")
    model: str = Field(description="模型名称")


class PersonalInfo(NoneToDefaultMixin, StrictBaseModel):
    """个人信息"""

    full_name: str = Field(default="", description="Full name")
    job_title: str = Field(default="", description="Target position / job title")
    phone: str = Field(default="", description="Phone number")
    email: str = Field(default="", description="Email address")
    salary: str = Field(default="", description="Expected salary")
    location: str = Field(default="", description="City / location")
    age: str = Field(default="", description="Age")
    gender: str = Field(default="", description="Gender")
    political_status: str = Field(default="", description="Political status")
    education_level: str = Field(default="", description="Education level")
    ethnicity: str = Field(default="", description="Ethnicity")
    hometown: str = Field(default="", description="Hometown")
    marital_status: str = Field(default="", description="Marital status")
    years_of_experience: str = Field(default="", description="Years of experience")
    wechat: str = Field(default="", description="WeChat")
    website: str = Field(default="", description="Personal website")
    linkedin: str = Field(default="", description="LinkedIn")


class Summary(NoneToDefaultMixin, StrictBaseModel):
    """个人简介"""

    text: str = Field(default="", description="Summary text")


class EducationItem(NoneToDefaultMixin, StrictBaseModel):
    """教育经历条目"""

    institution: str = Field(default="", description="School / institution name")
    degree: str = Field(default="", description="Degree")
    field: str = Field(default="", description="Major / field of study")
    location: str = Field(default="", description="Location")
    start_date: str = Field(default="", description="Start date")
    end_date: str = Field(default="", description="End date")
    gpa: str = Field(default="", description="GPA")
    highlights: list[str] = Field(
        default_factory=list, description="Honors / achievements"
    )


class WorkExperienceItem(NoneToDefaultMixin, StrictBaseModel):
    """工作经历条目"""

    company: str = Field(default="", description="Company / organization name")
    position: str = Field(default="", description="Job title / role")
    location: str = Field(default="", description="Work location")
    start_date: str = Field(default="", description="Start date")
    end_date: str = Field(default="", description="End date")
    current: bool = Field(default=False, description="Is current position")
    description: str = Field(default="", description="Job description")
    technologies: list[str] = Field(default_factory=list, description="Tech stack")
    highlights: list[str] = Field(
        default_factory=list, description="Achievements / highlights"
    )


class ProjectItem(NoneToDefaultMixin, StrictBaseModel):
    """项目经历条目"""

    name: str = Field(default="", description="Project name")
    url: str = Field(default="", description="Project URL")
    description: str = Field(default="", description="Project description")
    technologies: list[str] = Field(default_factory=list, description="Tech stack")
    highlights: list[str] = Field(
        default_factory=list, description="Project highlights / achievements"
    )
    start_date: str = Field(default="", description="Start date")
    end_date: str = Field(default="", description="End date")


class SkillCategory(NoneToDefaultMixin, StrictBaseModel):
    """技能分类"""

    name: str = Field(
        default="", description="Category name, e.g. Programming Languages"
    )
    skills: list[str] = Field(
        default_factory=list, description="Skills in this category"
    )


class LanguageItem(NoneToDefaultMixin, StrictBaseModel):
    """语言能力条目"""

    language: str = Field(default="", description="Language name")
    proficiency: str = Field(default="", description="Proficiency level")
    description: str = Field(default="", description="Additional description")


class CertificationItem(NoneToDefaultMixin, StrictBaseModel):
    """证书条目"""

    name: str = Field(default="", description="Certificate name")
    issuer: str = Field(default="", description="Issuing organization")
    date: str = Field(default="", description="Date obtained")
    description: str = Field(default="", description="Description")


class GitHubItem(NoneToDefaultMixin, StrictBaseModel):
    """GitHub 仓库条目"""

    repo_url: str = Field(default="", description="Repository URL")
    name: str = Field(default="", description="Repository name")
    stars: int = Field(default=0, description="Number of stars")
    language: str = Field(default="", description="Primary programming language")
    description: str = Field(default="", description="Repository description")


class CustomItem(NoneToDefaultMixin, StrictBaseModel):
    """自定义条目"""

    title: str = Field(default="", description="Entry title")
    date: str = Field(default="", description="Date")
    description: str = Field(default="", description="Description content")


class SubResumeResult(StrictBaseModel):
    """子简历的ai生成结果结构定义"""

    personal_info: PersonalInfo = Field(
        default_factory=PersonalInfo, description="Personal information"
    )
    summary: Summary = Field(default_factory=Summary, description="Personal summary")
    education: list[EducationItem] = Field(
        default_factory=list, description="Education experience"
    )
    work_experience: list[WorkExperienceItem] = Field(
        default_factory=list, description="Work experience"
    )
    projects: list[ProjectItem] = Field(
        default_factory=list, description="Project experience"
    )
    skills: list[SkillCategory] = Field(
        default_factory=list, description="Skills and abilities"
    )
    languages: list[LanguageItem] = Field(
        default_factory=list, description="Language proficiency"
    )
    certifications: list[CertificationItem] = Field(
        default_factory=list, description="Certifications"
    )
    github: list[GitHubItem] = Field(
        default_factory=list, description="GitHub repositories"
    )
    custom: list[CustomItem] = Field(default_factory=list, description="Custom entries")
