"""Parser Pydantic 模型。"""

from pydantic import Field, model_validator

from shared.types.mixins import NoneToDefaultMixin
from shared.types.strict_model import StrictBaseModel


class PersonalInfo(NoneToDefaultMixin, StrictBaseModel):
    """个人信息模型。"""

    full_name: str = Field(default="", description="Full name")
    job_title: str = Field(default="", description="Job title / target position")
    email: str = Field(default="", description="Email")
    phone: str = Field(default="", description="Phone number")
    location: str = Field(default="", description="City / location")
    salary: str = Field(default="", description="Expected salary")
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


class EducationItem(NoneToDefaultMixin, StrictBaseModel):
    """教育背景条目模型。"""

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


class SkillCategory(NoneToDefaultMixin, StrictBaseModel):
    """技能分类模型。"""

    name: str = Field(default="", description="Category name")
    skills: list[str] = Field(
        default_factory=list, description="Skills in this category"
    )


class ProjectItem(NoneToDefaultMixin, StrictBaseModel):
    """项目经历条目模型。"""

    name: str = Field(default="", description="Project name")
    description: str = Field(default="", description="Project description")
    technologies: list[str] = Field(default_factory=list, description="Tech stack")
    highlights: list[str] = Field(
        default_factory=list, description="Project highlights"
    )
    url: str = Field(default="", description="Project URL")
    start_date: str = Field(default="", description="Start date")
    end_date: str = Field(default="", description="End date")


class CertificationItem(NoneToDefaultMixin, StrictBaseModel):
    """资格证书条目模型。"""

    name: str = Field(default="", description="Certificate name")
    issuer: str = Field(default="", description="Issuing organization")
    date: str = Field(default="", description="Date obtained")
    description: str = Field(default="", description="Description")


class WorkExperienceItem(NoneToDefaultMixin, StrictBaseModel):
    """工作经历条目模型。"""

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


class LanguageItem(NoneToDefaultMixin, StrictBaseModel):
    """语言能力条目模型。"""

    language: str = Field(default="", description="Language name")
    proficiency: str = Field(default="", description="Proficiency level")
    description: str = Field(default="", description="Additional description")


class ParserResult(StrictBaseModel):
    """解析结果模型。"""

    @model_validator(mode="before")
    @classmethod
    def handle_none(cls, v):
        """接受 None 输入并返回空字典。"""
        if v is None:
            return {}
        return v

    personal_info: PersonalInfo = Field(
        default_factory=PersonalInfo, description="Personal information"
    )
    summary: str = Field(default="", description="Personal summary")
    work_experiences: list[WorkExperienceItem] | None = Field(
        default=None, description="Work experience"
    )
    education: list[EducationItem] | None = Field(default=None, description="Education")
    skills: list[SkillCategory] | None = Field(default=None, description="Skills")
    projects: list[ProjectItem] | None = Field(default=None, description="Projects")
    certifications: list[CertificationItem] | None = Field(
        default=None, description="Certifications"
    )
    languages: list[LanguageItem] | None = Field(default=None, description="Languages")
