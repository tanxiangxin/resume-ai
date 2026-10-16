"""解析任务执行服务。"""

import asyncio
import logging
import secrets
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from apps.parser.call_llm import executor_llm
from apps.parser.pdf_parser import pdf_parser
from apps.parser.schemas import ParserResult
from chiren_backend.platform.llm.client import SupportsStreamingMessages
from chiren_backend.platform.models import Resume
from chiren_backend.platform.resume_sections import (
    SectionConfig,
    create_resume_sections,
)
from chiren_backend.platform.task_state import (
    cleanup_task,
    update_task_error,
    update_task_result,
    update_task_status,
)
from chiren_backend.platform.work_records import update_work_status_in_new_session
from shared.types.resume import (
    CertificationsContent,
    EducationContent,
    LanguagesContent,
    PersonalInfo,
    ProjectsContent,
    SkillsContent,
    Summary,
    WorkExperienceContent,
)
from shared.types.task import TaskStatus

log = logging.getLogger(__name__)

_prefix_store: dict[str, str] = {}


def _get_prefix(section_type: str) -> str:
    """获取或生成 section 类型的随机前缀。"""
    if section_type not in _prefix_store:
        _prefix_store[section_type] = secrets.token_hex(4)
    return _prefix_store[section_type]


def _make_parser_section_configs(result: ParserResult) -> list[SectionConfig]:
    """构建 ParserResult 对应的 section 配置列表。"""
    configs: list[SectionConfig] = [
        SectionConfig(
            type="personal_info",
            title="个人信息",
            content_fn=lambda: result.personal_info.model_dump(),
            default_fn=lambda: PersonalInfo().model_dump(),
            field_name="personal_info",
        ),
        SectionConfig(
            type="summary",
            title="个人简介",
            content_fn=lambda: {"text": result.summary},
            default_fn=lambda: Summary().model_dump(),
            field_name="summary",
        ),
        SectionConfig(
            type="work_experience",
            title="工作经历",
            content_fn=lambda: _build_items_content(
                result.work_experiences, WorkExperienceContent, "work_experience"
            ),
            default_fn=lambda: WorkExperienceContent().model_dump(),
            field_name="work_experiences",
        ),
        SectionConfig(
            type="education",
            title="教育背景",
            content_fn=lambda: _build_items_content(
                result.education, EducationContent, "education"
            ),
            default_fn=lambda: EducationContent().model_dump(),
            field_name="education",
        ),
        SectionConfig(
            type="skills",
            title="技能特长",
            content_fn=lambda: _build_categories_content(result.skills),
            default_fn=lambda: SkillsContent().model_dump(),
            field_name="skills",
        ),
        SectionConfig(
            type="projects",
            title="项目经历",
            content_fn=lambda: _build_items_content(
                result.projects, ProjectsContent, "projects"
            ),
            default_fn=lambda: ProjectsContent().model_dump(),
            field_name="projects",
        ),
        SectionConfig(
            type="languages",
            title="语言能力",
            content_fn=lambda: _build_items_content(
                result.languages, LanguagesContent, "languages"
            ),
            default_fn=lambda: LanguagesContent().model_dump(),
            field_name="languages",
        ),
        SectionConfig(
            type="certifications",
            title="资格证书",
            content_fn=lambda: _build_items_content(
                result.certifications, CertificationsContent, "certifications"
            ),
            default_fn=lambda: CertificationsContent().model_dump(),
            field_name="certifications",
        ),
    ]
    return configs


def _build_items_content(items: list | None, content_cls: type, prefix: str) -> dict:
    """构建 items 类型的 section content。"""
    p = _get_prefix(prefix)

    if items:
        return content_cls(
            items=[
                _ensure_id(item.model_dump(), p, idx)
                for idx, item in enumerate(items, start=1)
            ]
        ).model_dump()
    return content_cls().model_dump()


def _build_categories_content(categories: list | None) -> dict:
    """构建 categories 类型的 section content（如 skills）。"""
    p = _get_prefix("skills")

    if categories:
        return SkillsContent(
            categories=[
                _ensure_id(cat.model_dump(), p, idx)
                for idx, cat in enumerate(categories, start=1)
            ]
        ).model_dump()
    return SkillsContent().model_dump()


def _ensure_id(obj: dict, prefix: str, index: int) -> dict:
    """确保对象有 id 字段。"""
    if "id" not in obj or not obj["id"]:
        obj["id"] = f"{prefix}-{index:04d}"
    return obj


def _create_resume_sections(
    db: AsyncSession, resume_id: str, result: ParserResult
) -> None:
    """创建简历的所有区块。

    按照预定义的固定顺序创建 section，缺失的 section 使用默认空内容填充。
    不自行 commit/rollback，由调用方管理事务。

    Args:
        db: 数据库会话。
        resume_id: 简历 ID。
        result: LLM 解析结果。
    """
    global _prefix_store
    _prefix_store = {}
    configs = _make_parser_section_configs(result)
    create_resume_sections(db, resume_id, result, configs)


def infer_parser_type(filename: str, content_type: str | None) -> str:
    """根据文件名和内容类型推断解析器类型。

    Args:
        filename: 上传文件的文件名。
        content_type: 文件的 MIME 类型。

    Returns:
        解析器类型标识符，如 "pdf"。

    Raises:
        ValueError: 不支持的文件类型。
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext == "pdf" or content_type == "application/pdf":
        return "pdf"

    raise ValueError(f"不支持的文件类型: {ext or content_type or '未知'}")


async def _execute_parse_flow(
    db: AsyncSession,
    task_id: str,
    file_path: str,
    client: SupportsStreamingMessages,
    model: str,
    template: str,
    title: str,
    *,
    delete_file: bool,
) -> None:
    """执行解析流程的公共逻辑。

    编排整个解析流程：PDF 文本提取 -> LLM 解析。

    Args:
        db: 数据库会话，调用方管理事务（commit/rollback）。
        task_id: 任务 ID。
        file_path: PDF 文件绝对路径。
        model: 模型名称。
        template: 模板名称。
        title: 简历标题。
        delete_file: 是否在清理时删除上传文件。
    """
    await update_task_status(task_id, TaskStatus.RUNNING)
    await update_work_status_in_new_session(task_id, TaskStatus.RUNNING)

    result = await pdf_parser.parse(file_path)
    result = await executor_llm(client, model, result["text"])

    # 创建简历
    resume = Resume(
        id=task_id,
        title=title,
        template=template,
    )
    db.add(resume)

    # 创建简历区块
    _create_resume_sections(db, task_id, result)

    await update_work_status_in_new_session(task_id, TaskStatus.SUCCESS)

    await update_task_result(task_id, {"resume_id": task_id})

    async def cleanup() -> None:
        if delete_file and file_path:
            Path(file_path).unlink(missing_ok=True)

    asyncio.create_task(cleanup_task(task_id, cleanup))


async def run_parser_task(
    db: AsyncSession,
    task_id: str,
    file_path: str,
    client: SupportsStreamingMessages,
    model: str,
    template: str,
    title: str,
) -> None:
    """后台解析任务执行函数。

    编排整个解析流程：PDF 文本提取 -> LLM 解析。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        file_path: PDF 文件绝对路径。
        client: LLM 客户端。
        model: 模型名称。
        template: 模板名称。
        title: 简历标题。
    """
    try:
        await _execute_parse_flow(
            db, task_id, file_path, client, model, template, title, delete_file=True
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        log.error("解析失败: %s", e)
        await update_work_status_in_new_session(
            task_id, TaskStatus.ERROR, error=f"解析失败: {str(e)}"
        )
        await update_task_error(task_id, f"解析失败: {str(e)}")
        asyncio.create_task(cleanup_task(task_id, None))
        raise


async def retry_parser_task(
    db: AsyncSession,
    task_id: str,
    file_path: str,
    client: SupportsStreamingMessages,
    model: str,
    template: str,
    title: str,
) -> None:
    """重试解析任务执行函数。

    读取已提取的文本内容，重新调用 LLM 解析。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        file_path: PDF 文件绝对路径（暂未使用，保留接口兼容性）。
        client: llm 客户端。
        model: 模型名称。
        template: 模板名称。
        title: 简历标题。
    """
    try:
        await _execute_parse_flow(
            db, task_id, file_path, client, model, template, title, delete_file=True
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        log.error("解析失败: %s", e)
        await update_work_status_in_new_session(
            task_id, TaskStatus.ERROR, error=f"解析失败: {str(e)}"
        )
        await update_task_error(task_id, f"解析失败: {str(e)}")
        asyncio.create_task(cleanup_task(task_id, None))
        raise
