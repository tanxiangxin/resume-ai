import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chiren_backend.platform.db import async_session
from chiren_backend.platform.models import ResumeSection, utc_now
from shared.types.base_tool import BaseTool, ToolExecutionContext, ToolResult
from shared.types.resume import (
    CertificationsContent,
    CertificationsSection,
    CustomContent,
    CustomSection,
    EducationContent,
    EducationSection,
    GitHubContent,
    GitHubSection,
    LanguagesContent,
    LanguagesSection,
    ProjectsContent,
    ProjectsSection,
    QrCodesContent,
    QrCodesSection,
    SkillsContent,
    SkillsSection,
    Summary,
    SummarySection,
    WorkExperienceContent,
    WorkExperienceSection,
)

_ALL_TYPES = [
    "personal_info",
    "summary",
    "work_experience",
    "projects",
    "education",
    "skills",
    "languages",
    "certifications",
    "qr_codes",
    "github",
    "custom",
]

# Section 类型映射: type -> (Section类, Content类或工厂函数)
_SECTION_TYPE_MAP: dict[str, tuple[type, type | Any]] = {
    "summary": (SummarySection, Summary),
    "work_experience": (WorkExperienceSection, WorkExperienceContent),
    "projects": (ProjectsSection, ProjectsContent),
    "education": (EducationSection, EducationContent),
    "skills": (SkillsSection, SkillsContent),
    "languages": (LanguagesSection, LanguagesContent),
    "certifications": (CertificationsSection, CertificationsContent),
    "github": (GitHubSection, GitHubContent),
    "qr_codes": (QrCodesSection, QrCodesContent),
}


def _create_section(
    section_type: str,
    resume_id: str,
    title: str,
    sort_order: int,
) -> tuple[
    SummarySection
    | ProjectsSection
    | EducationSection
    | SkillsSection
    | LanguagesSection
    | CertificationsSection
    | GitHubSection
    | QrCodesSection,
    type,
]:
    """
    工厂函数：根据 section_type 创建对应的 Section 实例。

    Args:
        section_type: section 类型标识
        resume_id: 简历 ID
        title: 显示标题
        sort_order: 排序序号

    Returns:
        (Section实例, Section类) 元组
    """
    section_cls, content_cls = _SECTION_TYPE_MAP[section_type]

    return section_cls(
        id=str(uuid.uuid4()),
        resume_id=resume_id,
        title=title,
        sort_order=sort_order,
        content=content_cls(),
        created_at=utc_now(),
        updated_at=utc_now(),
    ), section_cls


async def _restore_hidden_section(
    db: AsyncSession,
    resume_id: str,
    section_type: str,
) -> ResumeSection | None:
    """
    查找并恢复已存在但被隐藏的 section。

    Returns:
        已存在的 ResumeSection（已设置 visible=True）或 None
    """
    result = await db.execute(
        select(ResumeSection).where(
            ResumeSection.type == section_type,
            ResumeSection.resume_id == resume_id,
        )
    )
    resume_section = result.scalar_one_or_none()
    if resume_section is not None:
        resume_section.visible = True
    return resume_section


class AddSectionToolInput(BaseModel):
    type: str = Field(description="The type of section to add.")
    title: str = Field(description="The display title for the section.")


class AddSectionTool(BaseTool):
    name = "add_section"
    description = "Add a new section to the resume. Use this when the user wants to add a new section type. Available types: {type_examples}"
    input_model = AddSectionToolInput

    async def execute(
        self, arguments: AddSectionToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        existing_types = {s.get("type") for s in context.sections}
        if arguments.type in existing_types and arguments.type != "custom":
            return ToolResult(
                is_error=True,
                output=f"Section of type '{arguments.type}' already exists",
            )

        resume_id = context.sections[0]["resume_id"]
        next_sort_order = context.sections[-1]["sort_order"] + 1
        now = utc_now()

        async with async_session() as db:
            if arguments.type == "custom":
                section = CustomSection(
                    id=str(uuid.uuid4()),
                    resume_id=resume_id,
                    title=arguments.title,
                    sort_order=next_sort_order,
                    content=CustomContent(),
                    created_at=now,
                    updated_at=now,
                )
                db.add(ResumeSection.from_pydantic(section))
                context.sections.append(section.model_dump())
            else:
                resume_section = await _restore_hidden_section(
                    db, resume_id, arguments.type
                )
                if resume_section is not None:
                    resume_section.updated_at = now
                    db.add(resume_section)
                    context.sections.append(resume_section.to_pydantic().model_dump())
                else:
                    section, _ = _create_section(
                        arguments.type, resume_id, arguments.title, next_sort_order
                    )
                    db.add(ResumeSection.from_pydantic(section))
                    context.sections.append(section.model_dump())

            section_id = context.sections[-1]["id"]
            context.metadata["id_to_type"][section_id] = arguments.type
            context.sections = sorted(context.sections, key=lambda x: x["sort_order"])
            await db.commit()

        return ToolResult(output=f"Successfully added section {section_id}.")

    def to_api_schema_v2(self, sections: list[dict[str, Any]]) -> dict[str, Any]:
        existing_types = {s.get("type") for s in sections if s.get("type")}
        # 可添加的类型：排除已存在的，custom 必然出现
        available_types = [t for t in _ALL_TYPES if t not in existing_types]
        if "custom" not in available_types:
            available_types.append("custom")
        type_examples = '", "'.join(available_types)

        return {
            "name": self.name,
            "description": self.description.format(type_examples=type_examples),
            "input_schema": self.input_model.model_json_schema(),
        }
