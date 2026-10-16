"""导出服务，提供 JSON / TXT 格式导出"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chiren_backend.platform.models import Resume, ResumeSection


async def _fetch_resume_with_sections(
    resume_id: str, db: AsyncSession
) -> tuple[Resume, list[ResumeSection]]:
    """查询简历及其所有区块。

    Args:
        resume_id: 简历唯一标识。
        db: 数据库会话。

    Returns:
        (简历对象, 区块列表)

    Raises:
        ValueError: 简历不存在时抛出。
    """
    resume_result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise ValueError("简历不存在")

    section_result = await db.execute(
        select(ResumeSection)
        .where(ResumeSection.resume_id == resume_id)
        .order_by(ResumeSection.sort_order)
    )
    sections = list(section_result.scalars().all())
    return resume, sections


async def export_json(resume_id: str, db: AsyncSession) -> dict:
    """导出简历为 JSON 格式。

    Args:
        resume_id: 简历唯一标识。
        db: 数据库会话。

    Returns:
        包含简历字段和区块列表的字典。

    Raises:
        ValueError: 简历不存在时抛出。
    """
    resume, sections = await _fetch_resume_with_sections(resume_id, db)
    return {
        "resume": resume.to_pydantic().model_dump(),
        "sections": [section.to_pydantic().model_dump() for section in sections],
    }


async def export_txt(resume_id: str, db: AsyncSession) -> str:
    """导出简历为纯文本格式。

    按区块类型对内容进行格式化，隐藏区块将被跳过。

    Args:
        resume_id: 简历唯一标识。
        db: 数据库会话。

    Returns:
        格式化后的纯文本字符串。

    Raises:
        ValueError: 简历不存在时抛出。
    """
    resume, sections = await _fetch_resume_with_sections(resume_id, db)
    section_texts: list[str] = []

    for section in sections:
        if not section.visible:
            continue

        pydantic_section = section.to_pydantic()
        content = pydantic_section.content
        section_type = pydantic_section.type
        title = pydantic_section.title

        lines: list[str] = []

        if section_type == "personal_info":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            info = content
            for field, label in [
                (info.full_name, "姓名"),
                (info.job_title, "岗位"),
                (info.phone, "电话"),
                (info.email, "邮箱"),
            ]:
                if field:
                    lines.append(f"{label}: {field}")

        elif section_type == "summary":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            lines.append(content.text)

        elif section_type == "work_experience":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            for item in content.items:
                date_range = (
                    f"{item.start_date} - {item.end_date}"
                    if item.end_date
                    else item.start_date
                )
                lines.append(f"{item.company} - {item.position} ({date_range})")
                for hl in item.highlights:
                    lines.append(f"  • {hl}")

        elif section_type == "education":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            for item in content.items:
                date_range = (
                    f"{item.start_date} - {item.end_date}"
                    if item.end_date
                    else item.start_date
                )
                lines.append(f"{item.institution} - {item.degree} ({date_range})")
                for hl in item.highlights:
                    lines.append(f"  • {hl}")

        elif section_type == "projects":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            for item in content.items:
                line = item.name
                if item.url:
                    line += f" ({item.url})"
                lines.append(line)
                for hl in item.highlights:
                    lines.append(f"  • {hl}")

        elif section_type == "skills":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            for category in content.categories:
                skills_str = ", ".join(category.skills)
                lines.append(f"{category.name}: {skills_str}")

        elif section_type == "languages":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            for item in content.items:
                lines.append(f"{item.language} ({item.proficiency})")

        elif section_type == "certifications":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            for item in content.items:
                lines.append(f"{item.name} - {item.issuer} ({item.date})")

        elif section_type == "qr_codes":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            for item in content.items:
                lines.append(f"{item.label}: {item.url}")

        elif section_type == "github":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            for item in content.items:
                lines.append(f"{item.name} - {item.language} (★{item.stars})")

        elif section_type == "custom":
            if content is None:
                continue
            lines.append(f"== {title} ==")
            lines.append(content.title)
            if content.date:
                lines.append(content.date)
            if content.description:
                lines.append(content.description)

        if lines:
            section_texts.append("\n".join(lines))

    return "\n\n".join(section_texts)
