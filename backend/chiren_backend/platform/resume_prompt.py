"""简历提示词构建器。"""

from __future__ import annotations

from dataclasses import dataclass, field

from shared.types.resume import (
    CertificationsSection,
    CustomSection,
    EducationItem,
    EducationSection,
    GitHubSection,
    LanguagesSection,
    PersonalInfoSection,
    ProjectsSection,
    QrCodesSection,
    ResumeSectionSchema,
    SkillsSection,
    SummarySection,
    WorkExperienceItem,
    WorkExperienceSection,
)


@dataclass
class PersonalInfoFields:
    """个人信息字段配置."""

    full_name: bool = True
    age: bool = True
    gender: bool = True
    email: bool = True
    phone: bool = True
    education_level: bool = True
    job_title: bool = True
    salary: bool = True
    location: bool = True
    political_status: bool = True
    ethnicity: bool = True
    hometown: bool = True
    marital_status: bool = True
    years_of_experience: bool = True
    wechat: bool = True
    website: bool = True
    linkedin: bool = True


@dataclass
class ItemFields:
    """条目标段字段配置 (work_experience / education)."""

    location: bool = True


@dataclass
class SectionHeaderConfig:
    """Section 头部配置."""

    include_section_id: bool = False


@dataclass
class ResumePromptBuilder:
    """简历提示词构建器.

    Attributes:
        personal_info_fields: 个人信息字段配置
        item_fields: 条目字段配置
        section_header: Section 头部配置
        job_desc_prefix: JD 部分的前缀，默认为 "#Job Description:"
    """

    personal_info_fields: PersonalInfoFields = field(default_factory=PersonalInfoFields)
    item_fields: ItemFields = field(default_factory=ItemFields)
    section_header: SectionHeaderConfig = field(default_factory=SectionHeaderConfig)
    job_desc_prefix: str = "#Job Description:"

    def build_user_prompt(
        self,
        sections: list[ResumeSectionSchema],
        job_description: str,
        job_title: str | None = None,
    ) -> str:
        """构建用户提示词."""
        final_content_list = []

        for section in sections:
            if isinstance(section, PersonalInfoSection):
                lines = self._build_personal_info_section(section)
            elif isinstance(section, SummarySection):
                lines = self._build_summary_section(section)
            elif isinstance(section, WorkExperienceSection):
                lines = self._build_work_experience_section(section)
            elif isinstance(section, ProjectsSection):
                lines = self._build_projects_section(section)
            elif isinstance(section, EducationSection):
                lines = self._build_education_section(section)
            elif isinstance(section, SkillsSection):
                lines = self._build_skills_section(section)
            elif isinstance(section, LanguagesSection):
                lines = self._build_languages_section(section)
            elif isinstance(section, CertificationsSection):
                lines = self._build_certifications_section(section)
            elif isinstance(section, GitHubSection):
                lines = self._build_github_section(section)
            elif isinstance(section, QrCodesSection):
                lines = self._build_qrcodes_section(section)
            elif isinstance(section, CustomSection):
                lines = self._build_custom_section(section)
            else:
                continue

            final_content_list.append("\n".join(lines))

        user_prompt = "\n\n".join(final_content_list)
        return f"{self.job_desc_prefix}\n---\n{job_description}\n---\n\n{user_prompt}"

    def _build_section_header(self, section: ResumeSectionSchema) -> list[str]:
        """构建 section 通用头部."""
        lines = [
            "---",
            f"# {section.type} - {section.title}",
        ]
        if self.section_header.include_section_id:
            lines.append(f"section_id: {section.id}")
        return lines

    def _append_section_footer(self, lines: list[str]) -> None:
        """追加 section 尾部."""
        lines.append("---")

    def _build_personal_info_section(self, section: PersonalInfoSection) -> list[str]:
        """构建个人信息 section."""
        lines = self._build_section_header(section)

        if section.content:
            content = section.content
            cfg = self.personal_info_fields

            # 按配置收集字段
            optional_fields: list[tuple[str, str]] = []
            if cfg.full_name and content.full_name:
                optional_fields.append(("name", content.full_name))
            if cfg.age and content.age:
                optional_fields.append(("age", content.age))
            if cfg.gender and content.gender:
                optional_fields.append(("gender", content.gender))
            if cfg.email and content.email:
                optional_fields.append(("email", content.email))
            if cfg.phone and content.phone:
                optional_fields.append(("phone", content.phone))
            if cfg.education_level and content.education_level:
                optional_fields.append(("education_level", content.education_level))
            if cfg.job_title and content.job_title:
                optional_fields.append(("job_title", content.job_title))
            if cfg.salary and content.salary:
                optional_fields.append(("salary", content.salary))
            if cfg.location and content.location:
                optional_fields.append(("location", content.location))
            if cfg.political_status and content.political_status:
                optional_fields.append(("political_status", content.political_status))
            if cfg.ethnicity and content.ethnicity:
                optional_fields.append(("ethnicity", content.ethnicity))
            if cfg.hometown and content.hometown:
                optional_fields.append(("hometown", content.hometown))
            if cfg.marital_status and content.marital_status:
                optional_fields.append(("marital_status", content.marital_status))
            if cfg.years_of_experience and content.years_of_experience:
                optional_fields.append(
                    ("years_of_experience", content.years_of_experience)
                )
            if cfg.wechat and content.wechat:
                optional_fields.append(("wechat", content.wechat))
            if cfg.website and content.website:
                optional_fields.append(("website", content.website))
            if cfg.linkedin and content.linkedin:
                optional_fields.append(("linkedin", content.linkedin))

            for field_name, field_value in optional_fields:
                lines.append(f"{field_name}: {field_value}")
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines

    def _build_summary_section(self, section: SummarySection) -> list[str]:
        """构建个人简介 section."""
        lines = self._build_section_header(section)

        if section.content and section.content.text:
            lines.append(f"text: {section.content.text}")
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines

    def _build_work_experience_section(
        self, section: WorkExperienceSection
    ) -> list[str]:
        """构建工作经历 section."""
        lines = self._build_section_header(section)

        if section.content and section.content.items:
            for idx, item in enumerate(section.content.items):
                item_lines = self._format_work_experience_item(item, idx + 1)
                lines.extend(item_lines)
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines

    def _format_work_experience_item(
        self, item: WorkExperienceItem, idx: int
    ) -> list[str]:
        """格式化单个工作经历条目."""
        lines = [
            f"## [{idx}] {item.company}",
            f"position: {item.position}",
        ]

        if self.item_fields.location and item.location:
            lines.append(f"location: {item.location}")

        date_range = _format_date_range(item.start_date, item.end_date, item.current)
        lines.append(f"date: {date_range}")

        if item.description:
            lines.append(f"description: {item.description}")

        if item.highlights:
            lines.append("highlights:")
            for h in item.highlights:
                lines.append(f"  - {h}")

        return lines

    def _build_projects_section(self, section: ProjectsSection) -> list[str]:
        """构建项目经历 section."""
        lines = self._build_section_header(section)

        if section.content and section.content.items:
            for idx, item in enumerate(section.content.items):
                item_lines = _format_project_item(item, idx + 1)
                lines.extend(item_lines)
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines

    def _build_education_section(self, section: EducationSection) -> list[str]:
        """构建教育经历 section."""
        lines = self._build_section_header(section)

        if section.content and section.content.items:
            for idx, item in enumerate(section.content.items):
                item_lines = self._format_education_item(item, idx + 1)
                lines.extend(item_lines)
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines

    def _format_education_item(self, item: EducationItem, idx: int) -> list[str]:
        """格式化单个教育经历条目."""
        lines = [
            f"## [{idx}] {item.institution}",
        ]

        if item.degree:
            lines.append(f"degree: {item.degree}")

        if item.field:
            lines.append(f"field: {item.field}")

        if self.item_fields.location and item.location:
            lines.append(f"location: {item.location}")

        if item.start_date or item.end_date:
            date_range = (
                f"{item.start_date} - {item.end_date}"
                if item.end_date
                else item.start_date
            )
            lines.append(f"date: {date_range}")

        if item.gpa:
            lines.append(f"gpa: {item.gpa}")

        if item.highlights:
            lines.append("highlights:")
            for h in item.highlights:
                lines.append(f"  - {h}")

        return lines

    def _build_skills_section(self, section: SkillsSection) -> list[str]:
        """构建技能 section."""
        lines = self._build_section_header(section)

        if section.content and section.content.categories:
            for category in section.content.categories:
                if category.name and category.skills:
                    lines.append(f"## {category.name}")
                    lines.append(f"skills: {', '.join(category.skills)}")
                elif category.name:
                    lines.append(f"## {category.name}")
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines

    def _build_languages_section(self, section: LanguagesSection) -> list[str]:
        """构建语言能力 section."""
        lines = self._build_section_header(section)

        if section.content and section.content.items:
            for item in section.content.items:
                item_lines = [
                    f"## {item.language}",
                ]
                if item.proficiency:
                    item_lines.append(f"proficiency: {item.proficiency}")
                if item.description:
                    item_lines.append(f"description: {item.description}")
                lines.extend(item_lines)
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines

    def _build_certifications_section(
        self, section: CertificationsSection
    ) -> list[str]:
        """构建证书 section."""
        lines = self._build_section_header(section)

        if section.content and section.content.items:
            for idx, item in enumerate(section.content.items):
                lines.append(f"## [{idx + 1}] {item.name}")
                if item.issuer:
                    lines.append(f"issuer: {item.issuer}")
                if item.date:
                    lines.append(f"date: {item.date}")
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines

    def _build_github_section(self, section: GitHubSection) -> list[str]:
        """构建 GitHub section."""
        lines = self._build_section_header(section)

        if section.content and section.content.items:
            for item in section.content.items:
                lines.append(f"## {item.name}")
                if item.repo_url:
                    lines.append(f"url: {item.repo_url}")
                if item.description:
                    lines.append(f"description: {item.description}")
                if item.language:
                    lines.append(f"language: {item.language}")
                if item.stars:
                    lines.append(f"stars: {item.stars}")
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines

    def _build_qrcodes_section(self, section: QrCodesSection) -> list[str]:
        """构建二维码 section."""
        lines = self._build_section_header(section)

        if section.content and section.content.items:
            for item in section.content.items:
                lines.append(f"## {item.label}")
                if item.url:
                    lines.append(f"url: {item.url}")
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines

    def _build_custom_section(self, section: CustomSection) -> list[str]:
        """构建自定义 section."""
        lines = self._build_section_header(section)

        if section.content and section.content.items:
            for idx, item in enumerate(section.content.items):
                item_lines = [
                    f"## [{idx + 1}] {item.title}",
                ]
                if item.date:
                    item_lines.append(f"date: {item.date}")
                if item.description:
                    item_lines.append(f"description: {item.description}")
                lines.extend(item_lines)
        else:
            lines.append("[user did not provide any content]")

        self._append_section_footer(lines)
        return lines


def _format_project_item(item, idx: int) -> list[str]:
    """格式化单个项目条目."""
    lines = [
        f"## [{idx}] {item.name}",
    ]

    if item.url:
        lines.append(f"url: {item.url}")

    if item.description:
        lines.append(f"description: {item.description}")

    if item.technologies:
        lines.append(f"technologies: {', '.join(item.technologies)}")

    if item.start_date or item.end_date:
        date_range = (
            f"{item.start_date} - {item.end_date}"
            if item.end_date
            else f"{item.start_date} - 至今"
        )
        lines.append(f"date: {date_range}")

    if item.highlights:
        lines.append("highlights:")
        for h in item.highlights:
            lines.append(f"  - {h}")

    return lines


def _format_date_range(start_date: str, end_date: str, current: bool) -> str:
    """格式化日期范围."""
    if current:
        return f"{start_date} - 至今" if start_date else "至今"
    if end_date:
        return f"{start_date} - {end_date}" if start_date else end_date
    return start_date if start_date else ""
