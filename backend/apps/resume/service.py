"""简历相关业务逻辑"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chiren_backend.platform.models import ResumeSection
from shared.types.resume import (
    EducationContent,
    EducationSection,
    PersonalInfo,
    PersonalInfoSection,
    ProjectsContent,
    ProjectsSection,
    SkillsContent,
    SkillsSection,
    Summary,
    SummarySection,
    WorkExperienceContent,
    WorkExperienceSection,
)


async def create_default_sections(resume_id: str, db: AsyncSession) -> None:
    """为新简历创建默认的 section 列表"""
    sections = [
        PersonalInfoSection(
            id=str(uuid.uuid4()),
            resume_id=resume_id,
            title="个人信息",
            sort_order=0,
            content=PersonalInfo(),
        ),
        SummarySection(
            id=str(uuid.uuid4()),
            resume_id=resume_id,
            title="个人简介",
            sort_order=1,
            content=Summary(),
        ),
        WorkExperienceSection(
            id=str(uuid.uuid4()),
            resume_id=resume_id,
            title="工作经历",
            sort_order=2,
            content=WorkExperienceContent(),
        ),
        EducationSection(
            id=str(uuid.uuid4()),
            resume_id=resume_id,
            title="教育背景",
            sort_order=3,
            content=EducationContent(),
        ),
        SkillsSection(
            id=str(uuid.uuid4()),
            resume_id=resume_id,
            title="技能特长",
            sort_order=4,
            content=SkillsContent(),
        ),
        ProjectsSection(
            id=str(uuid.uuid4()),
            resume_id=resume_id,
            title="项目经历",
            sort_order=5,
            content=ProjectsContent(),
        ),
    ]

    for section in sections:
        db.add(ResumeSection.from_pydantic(section))


async def copy_sections_from_workspace(
    source_resume_id: str, target_resume_id: str, db: AsyncSession
) -> None:
    """从源简历复制所有 sections 到目标简历（内容复制，id 重新生成）"""
    from chiren_backend.platform.models import ResumeSection

    result = await db.execute(
        select(ResumeSection).where(ResumeSection.resume_id == source_resume_id)
    )
    source_sections = result.scalars().all()

    for section in source_sections:
        new_section = ResumeSection(
            id=str(uuid.uuid4()),
            resume_id=target_resume_id,
            title=section.title,
            type=section.type,
            sort_order=section.sort_order,
            visible=section.visible,
            content=section.content,
        )
        db.add(new_section)
