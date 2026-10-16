from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    TypeAdapter,
    alias_generators,
    model_validator,
)

from shared.types.strict_model import StrictBaseModel


class ResumeSchema(BaseModel):
    """简历模型"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    id: str | None = Field(default=None, description="简历唯一标识")
    workspace_id: str | None = Field(
        default=None, description="所属 Workspace ID，为空表示本身就是 Workspace"
    )
    title: str = Field(default="未命名简历", description="简历标题")
    theme_config: dict[str, Any] = Field(default_factory=dict, description="主题配置")
    template: str = Field(default="classic", description="模板名称")
    is_default: bool = Field(default=False, description="是否为用户的默认简历")
    language: str = Field(default="zh", description="简历语言")
    share_token: str | None = Field(
        default=None, description="分享链接 Token，为空表示未开启分享"
    )
    is_public: bool = Field(default=False, description="是否公开简历")
    share_password: str | None = Field(
        default=None, description="分享密码，为空表示无密码"
    )
    view_count: int = Field(default=0, description="公开/分享页面的浏览次数")
    meta_info: dict[str, Any] | None = Field(
        default=None, description="子简历元数据，包含 JD、目标公司等"
    )
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="最后更新时间")


class WorkExperienceItem(StrictBaseModel):
    """工作经历"""

    id: str = Field(default="", description="工作经历ID")
    company: str = Field(default="", description="公司名称")
    position: str = Field(default="", description="职位名称")
    location: str = Field(default="", description="工作地点")
    start_date: str = Field(default="", description="开始时间")
    end_date: str = Field(default="", description="结束时间")
    current: bool = Field(default=False, description="是否至今")
    description: str = Field(default="", description="工作描述")
    technologies: list[str] = Field(default_factory=list, description="技术栈")
    highlights: list[str] = Field(default_factory=list, description="工作 highlights")


class EducationItem(StrictBaseModel):
    """教育经历"""

    id: str = Field(default="", description="教育经历ID")
    institution: str = Field(default="", description="学校名称")
    degree: str = Field(default="", description="学位")
    field: str = Field(default="", description="专业")
    location: str = Field(default="", description="地点")
    start_date: str = Field(default="", description="开始时间")
    end_date: str = Field(default="", description="结束时间")
    gpa: str = Field(default="", description="GPA")
    highlights: list[str] = Field(default_factory=list, description="亮点")


class ProjectItem(StrictBaseModel):
    """项目经历"""

    id: str = Field(default="", description="项目ID")
    name: str = Field(default="", description="项目名称")
    url: str = Field(default="", description="项目链接")
    description: str = Field(default="", description="项目描述")
    technologies: list[str] = Field(default_factory=list, description="技术栈")
    highlights: list[str] = Field(default_factory=list, description="亮点")
    start_date: str = Field(default="", description="开始时间")
    end_date: str = Field(default="", description="结束时间")


class SkillItem(StrictBaseModel):
    """技能项"""

    id: str = Field(default="", description="技能ID")
    name: str = Field(default="", description="技能名称")
    skills: list[str] = Field(default_factory=list, description="技能列表")


class LanguageItem(StrictBaseModel):
    """语言能力"""

    id: str = Field(default="", description="语言ID")
    language: str = Field(default="", description="语言")
    proficiency: str = Field(default="", description="熟练程度")
    description: str = Field(default="", description="描述")


class CertificationItem(StrictBaseModel):
    """证书"""

    id: str = Field(default="", description="证书ID")
    name: str = Field(default="", description="证书名称")
    issuer: str = Field(default="", description="颁发机构")
    date: str = Field(default="", description="获得日期")
    description: str = Field(default="", description="描述")


class QrCodeItem(StrictBaseModel):
    """二维码"""

    id: str = Field(default="", description="二维码ID")
    label: str = Field(default="", description="二维码标签，如「微信」「主页」")
    url: str = Field(default="", description="二维码指向的链接")
    image_url: str = Field(default="", description="已生成的二维码图片地址")


class GitHubItem(StrictBaseModel):
    """GitHub 仓库"""

    id: str = Field(default="", description="仓库ID")
    repo_url: str = Field(default="", description="仓库链接")
    name: str = Field(default="", description="仓库名")
    stars: int = Field(default=0, description="星标数")
    language: str = Field(default="", description="编程语言")
    description: str = Field(default="", description="仓库描述")


# ══════════════════════════════════════════════════════════════
#  Content 模型（全部是 dict，列表统一放在 items / categories）
# ══════════════════════════════════════════════════════════════


class PersonalInfo(StrictBaseModel):
    """个人信息"""

    full_name: str = Field(default="", description="姓名")
    job_title: str = Field(default="", description="预期岗位")
    phone: str = Field(default="", description="手机号")
    email: str = Field(default="", description="邮箱")
    salary: str = Field(default="", description="期望薪资")
    location: str = Field(default="", description="城市")
    age: str = Field(default="", description="年龄")
    gender: str = Field(default="", description="性别")
    political_status: str = Field(default="", description="政治面貌")
    education_level: str = Field(default="", description="学历")
    ethnicity: str = Field(default="", description="民族")
    hometown: str = Field(default="", description="籍贯")
    marital_status: str = Field(default="", description="婚姻状况")
    years_of_experience: str = Field(default="", description="工作年限")
    wechat: str = Field(default="", description="微信号")
    website: str = Field(default="", description="个人网站")
    linkedin: str = Field(default="", description="LinkedIn")
    avatar: str = Field(default="", description="头像")


class Summary(StrictBaseModel):
    """个人简介"""

    text: str = Field(default="", description="简介")


class WorkExperienceContent(StrictBaseModel):
    """工作经历 content"""

    items: list[WorkExperienceItem] = Field(
        default_factory=list, description="工作经历列表"
    )


class ProjectsContent(StrictBaseModel):
    """项目经历 content"""

    items: list[ProjectItem] = Field(default_factory=list, description="项目列表")


class EducationContent(StrictBaseModel):
    """教育经历 content"""

    items: list[EducationItem] = Field(default_factory=list, description="教育经历列表")


class SkillsContent(StrictBaseModel):
    """技能 content，子字段用 categories"""

    categories: list[SkillItem] = Field(
        default_factory=list, description="技能分类列表"
    )


class LanguagesContent(StrictBaseModel):
    """语言能力 content"""

    items: list[LanguageItem] = Field(default_factory=list, description="语言列表")


class CertificationsContent(StrictBaseModel):
    """证书 content"""

    items: list[CertificationItem] = Field(default_factory=list, description="证书列表")


class QrCodesContent(StrictBaseModel):
    """二维码 content"""

    items: list[QrCodeItem] = Field(default_factory=list, description="二维码列表")


class GitHubContent(StrictBaseModel):
    """GitHub content"""

    items: list[GitHubItem] = Field(default_factory=list, description="仓库列表")


class CustomContent(StrictBaseModel):
    """自定义 content"""

    id: str = Field(default="", description="自定义项ID")
    title: str = Field(default="", description="标题")
    date: str = Field(default="", description="日期")
    description: str = Field(default="", description="描述")


# ══════════════════════════════════════════════════════════════
#  核心基类：content JSON 字符串自动反序列化
# ══════════════════════════════════════════════════════════════


class ResumeSectionBase(BaseModel):
    """
    数据库里 content 存的是 JSON 字符串。
    model_validator(mode="before") 在字段校验之前先把它 parse 成 dict，
    这样子类的 content 字段就能正常做类型校验了。
    """

    id: str = Field(description="区块唯一标识")
    resume_id: str = Field(description="所属简历 ID")
    title: str = Field(description="区块显示标题")
    sort_order: int = Field(default=0, description="排序序号，越小越靠前")
    visible: bool = Field(default=True, description="是否可见")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _deserialize_content(cls, values: Any) -> Any:
        if isinstance(values, dict) and isinstance(values.get("content"), str):
            try:
                values = {**values, "content": json.loads(values["content"])}
            except json.JSONDecodeError as e:
                raise ValueError(f"content 字段不是合法 JSON：{e}") from e
        return values


# ══════════════════════════════════════════════════════════════
#  各具体 Section 子类
# ══════════════════════════════════════════════════════════════


class PersonalInfoSection(ResumeSectionBase):
    type: Literal["personal_info"] = "personal_info"
    content: PersonalInfo | None = Field(default=None)


class SummarySection(ResumeSectionBase):
    type: Literal["summary"] = "summary"
    content: Summary | None = Field(default=None)


class WorkExperienceSection(ResumeSectionBase):
    type: Literal["work_experience"] = "work_experience"
    content: WorkExperienceContent | None = Field(default=None)


class ProjectsSection(ResumeSectionBase):
    type: Literal["projects"] = "projects"
    content: ProjectsContent | None = Field(default=None)


class EducationSection(ResumeSectionBase):
    type: Literal["education"] = "education"
    content: EducationContent | None = Field(default=None)


class SkillsSection(ResumeSectionBase):
    type: Literal["skills"] = "skills"
    content: SkillsContent | None = Field(default=None)


class LanguagesSection(ResumeSectionBase):
    type: Literal["languages"] = "languages"
    content: LanguagesContent | None = Field(default=None)


class CertificationsSection(ResumeSectionBase):
    type: Literal["certifications"] = "certifications"
    content: CertificationsContent | None = Field(default=None)


class QrCodesSection(ResumeSectionBase):
    type: Literal["qr_codes"] = "qr_codes"
    content: QrCodesContent | None = Field(default=None)


class GitHubSection(ResumeSectionBase):
    type: Literal["github"] = "github"
    content: GitHubContent | None = Field(default=None)


class CustomSection(ResumeSectionBase):
    type: Literal["custom"] = "custom"
    content: CustomContent | None = Field(default=None)


# ══════════════════════════════════════════════════════════════
#  Discriminated Union 入口类型
# ══════════════════════════════════════════════════════════════

ResumeSectionSchema = Annotated[
    Annotated[PersonalInfoSection, Tag("personal_info")]
    | Annotated[SummarySection, Tag("summary")]
    | Annotated[WorkExperienceSection, Tag("work_experience")]
    | Annotated[ProjectsSection, Tag("projects")]
    | Annotated[EducationSection, Tag("education")]
    | Annotated[SkillsSection, Tag("skills")]
    | Annotated[LanguagesSection, Tag("languages")]
    | Annotated[CertificationsSection, Tag("certifications")]
    | Annotated[QrCodesSection, Tag("qr_codes")]
    | Annotated[GitHubSection, Tag("github")]
    | Annotated[CustomSection, Tag("custom")],
    Discriminator("type"),
]


# ── type alias，方便在其他地方 import ─────────────────────────
ResumeSectionType = (
    PersonalInfoSection
    | SummarySection
    | WorkExperienceSection
    | ProjectsSection
    | EducationSection
    | SkillsSection
    | LanguagesSection
    | CertificationsSection
    | QrCodesSection
    | GitHubSection
    | CustomSection
)

section_adapter = TypeAdapter(ResumeSectionSchema)

SECTION_TYPE_TO_MODEL: dict[str, type[BaseModel]] = {
    "personal_info": PersonalInfo,
    "summary": Summary,
    "work_experience": WorkExperienceItem,
    "education": EducationItem,
    "projects": ProjectItem,
    "certifications": CertificationItem,
    "languages": LanguageItem,
    "github": GitHubItem,
    "custom": CustomContent,
    "skills": SkillItem,
}
