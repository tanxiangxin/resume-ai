"""简历区块工厂函数。"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from chiren_backend.platform.models import ResumeSection


@dataclass
class SectionConfig:
    """单个简历区块的配置。

    Attributes:
        type: 区块类型标识，如 "personal_info"、"work_experience"。
        title: 区块显示标题。
        content_fn: 从解析结果提取内容的函数，无参数，返回 dict。
        default_fn: 当字段为空时使用的默认内容函数，无参数，返回 dict。
        field_name: 直接指定 result 中的字段名，优先级高于 field_name_fn。
    """

    type: str
    title: str
    content_fn: Callable[[], dict]
    default_fn: Callable[[], dict]
    field_name: str | None = None


def create_resume_sections(
    db: AsyncSession,
    resume_id: str,
    result: BaseModel,
    section_configs: list[SectionConfig],
    field_name_fn: Callable[[str], str] | None = None,
    extra_sections_fn: Callable[[Any, str, int], list[ResumeSection]] | None = None,
) -> None:
    """创建简历的所有区块。

    按照预定义的固定顺序创建 section，缺失的 section 使用默认空内容填充。
    不自行 commit/rollback，由调用方管理事务。

    Args:
        db: 数据库会话。
        resume_id: 简历 ID。
        result: LLM 解析结果（ParserResult 或 SubResumeResult）。
        section_configs: section 配置列表。
        field_name_fn: 可选，将 section type 映射到 result 字段名的函数。
            当 SectionConfig.field_name 为 None 时使用。
        extra_sections_fn: 可选，创建额外 section 的函数（如 custom）。
            签名：fn(result, resume_id, start_sort_order) -> list[ResumeSection]
    """
    sections = []
    sort_order = 0

    for config in section_configs:
        section_type = config.type

        if config.field_name is not None:
            field_name = config.field_name
        elif field_name_fn is not None:
            field_name = field_name_fn(section_type)
        else:
            field_name = section_type

        field_value = getattr(result, field_name, None)

        if field_value is not None:
            content = config.content_fn()
        else:
            content = config.default_fn()

        sections.append(
            ResumeSection(
                resume_id=resume_id,
                type=section_type,
                title=config.title,
                sort_order=sort_order,
                visible=True,
                content=json.dumps(content, ensure_ascii=False),
            )
        )
        sort_order += 1

    if extra_sections_fn is not None:
        extra = extra_sections_fn(result, resume_id, sort_order)
        sections.extend(extra)

    db.add_all(sections)
