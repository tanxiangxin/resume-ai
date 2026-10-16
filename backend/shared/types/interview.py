from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from shared.types.strict_model import StrictBaseModel


class InterviewCollectionSchema(StrictBaseModel):
    """面试集合体 DTO"""

    id: str = Field(description="面试集合唯一标识")
    name: str = Field(description="面试集合名称")
    sub_resume_id: str = Field(description="关联的子简历ID")
    status: str = Field(
        default="not_started",
        description="状态：not_started/in_progress/completed",
    )
    meta_info: dict[str, Any] | None = Field(
        default=None,
        description="集合元数据，包含总体面试总结等",
    )
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")


class InterviewRoundSchema(StrictBaseModel):
    """面试轮次 DTO"""

    id: str = Field(description="面试轮次ID，同时也是会话ID")
    interview_collection_id: str = Field(description="所属面试集合ID")
    name: str = Field(description="轮次名称，如'技术一面'")
    interviewer_name: str = Field(description="面试官名称")
    interviewer_title: str = Field(default="", description="面试官头衔")
    interviewer_bio: str = Field(default="", description="面试官简介")
    question_style: str = Field(default="", description="提问风格")
    assessment_dimensions: list[str] = Field(
        default_factory=list, description="考察维度"
    )
    personality_traits: list[str] = Field(default_factory=list, description="性格特征")
    status: str = Field(
        default="not_started",
        description="状态：not_started/in_progress/completed",
    )
    sort_order: int = Field(default=0, description="排序序号")
    meta_info: dict[str, Any] | None = Field(
        default=None,
        description="轮次元数据，包含面试摘要等",
    )
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")
