from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from shared.types.cover_letter import (
    CoverLetterBatchSchema,
    CoverLetterGenerationParams,
)
from shared.types.greeting import GreetingBatchSchema, GreetingGenerationResult
from shared.types.interview import (
    InterviewCollectionSchema,
    InterviewRoundSchema,
)
from shared.types.jd_analysis import (
    JdRequirementItem,
    JobDescriptionAnalysisSchema,
    KeywordMatchItem,
    KeywordMissingItem,
    PartialMatchItem,
    SkillMatchItem,
    StrengthItem,
    SuggestionItem,
)
from shared.types.jd_profile import (
    JdProfileData,
    JobDescriptionProfileSchema,
)
from shared.types.messages import ConversationMessageSchema
from shared.types.resume import ResumeSchema, ResumeSectionSchema, section_adapter

S = TypeVar("S", bound=BaseModel)


def _drop_legacy_raw_text(value: Any) -> Any:
    """Read old JSON after removing the retired field-level provenance keys."""
    if isinstance(value, dict):
        return {
            key: _drop_legacy_raw_text(child)
            for key, child in value.items()
            if key not in {"raw_text", "rawText"}
        }
    if isinstance(value, list):
        return [_drop_legacy_raw_text(child) for child in value]
    return value

# 上海时区 (UTC+8)
SHANGHAI_TZ = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """返回当前上海时区时间。"""
    return datetime.now(SHANGHAI_TZ)


class PydanticMixin[S: BaseModel]:
    def to_pydantic(self) -> S:
        raise NotImplementedError

    @classmethod
    def from_pydantic(cls, schema: S) -> PydanticMixin[S]:
        raise NotImplementedError


class Base(DeclarativeBase):
    __abstract__ = True


class Resume(PydanticMixin, Base):
    """简历数据库模型"""

    __tablename__ = "resumes"
    __table_args__ = (
        Index("ix_resumes_workspace_created_at", "workspace_id", "created_at"),
        Index("ix_resumes_template", "template"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="简历唯一标识，主键",
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("resumes.id"),
        nullable=True,
        index=True,
        comment="所属 Workspace（顶级简历）的 ID，为空表示本身就是 Workspace",
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="未命名简历",
        comment="简历标题",
    )
    template: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="two-column",
        comment="前端简历模板名称",
    )
    theme_config: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
        comment="主题配置，JSON 字符串",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否为用户的默认简历",
    )
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="zh",
        comment="简历语言",
    )
    share_token: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        comment="分享链接 Token，为空表示未开启分享",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否公开简历",
    )
    share_password: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="分享密码（可选），为空表示无密码",
    )
    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="公开/分享页面的浏览次数",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="最后更新时间",
    )
    meta_info: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="子简历元数据，包含 JD、目标公司等",
    )

    workspace = relationship(
        "Resume",
        remote_side=[id],
        back_populates="versions",
    )
    versions = relationship(
        "Resume",
        back_populates="workspace",
        foreign_keys=[workspace_id],
        cascade="all, delete-orphan",
    )
    sections = relationship(
        "ResumeSection", back_populates="resume", cascade="all, delete-orphan"
    )
    job_description_analyses = relationship(
        "JobDescriptionAnalysis",
        back_populates="resume",
        cascade="all, delete-orphan",
    )
    job_description_profiles = relationship(
        "JobDescriptionProfile",
        back_populates="resume",
        cascade="all, delete-orphan",
    )
    interview_collections = relationship(
        "InterviewCollection",
        back_populates="resume",
        foreign_keys="InterviewCollection.sub_resume_id",
        cascade="all, delete-orphan",
    )
    greeting_batches = relationship(
        "GreetingGenerationBatch",
        back_populates="resume",
        cascade="all, delete-orphan",
    )
    cover_letter_batches = relationship(
        "CoverLetterGenerationBatch",
        back_populates="resume",
        cascade="all, delete-orphan",
    )

    def to_pydantic(self) -> ResumeSchema:
        return ResumeSchema(
            id=self.id,
            workspace_id=self.workspace_id,
            title=self.title,
            template=self.template,
            theme_config=json.loads(self.theme_config),
            is_default=self.is_default,
            language=self.language,
            share_token=self.share_token,
            is_public=self.is_public,
            share_password=self.share_password,
            view_count=self.view_count,
            created_at=self.created_at,
            updated_at=self.updated_at,
            meta_info=self.meta_info,
        )

    @classmethod
    def from_pydantic(cls, schema: ResumeSchema) -> Resume:
        created = schema.created_at or utc_now()
        updated = schema.updated_at or utc_now()

        return cls(
            id=schema.id,
            workspace_id=schema.workspace_id,
            title=schema.title,
            template=schema.template,
            theme_config=json.dumps(schema.theme_config, ensure_ascii=False),
            is_default=schema.is_default,
            language=schema.language,
            share_token=schema.share_token,
            is_public=schema.is_public,
            share_password=schema.share_password,
            view_count=schema.view_count,
            created_at=created,
            updated_at=updated,
            meta_info=schema.meta_info,
        )


class ResumeSection(PydanticMixin, Base):
    """简历区块数据库模型"""

    __tablename__ = "resume_sections"
    __table_args__ = (
        Index("ix_resume_sections_resume_sort", "resume_id", "sort_order"),
        Index(
            "ix_resume_sections_resume_visible_sort",
            "resume_id",
            "visible",
            "sort_order",
        ),
        Index("ix_resume_sections_resume_type", "resume_id", "type"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="区块唯一标识",
    )
    resume_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resumes.id"),
        nullable=False,
        index=True,
        comment="所属简历ID",
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="区块类型，如 personal_info、work_experience 等",
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="区块显示标题",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="排序序号，越小越靠前",
    )
    visible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否可见",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
        comment="区块内容，JSON 字符串",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="更新时间",
    )

    resume = relationship("Resume", back_populates="sections")

    def to_pydantic(self) -> ResumeSectionSchema:
        data = dict(
            id=self.id,
            resume_id=self.resume_id,
            title=self.title,
            type=self.type,
            sort_order=self.sort_order,
            visible=self.visible,
            content=json.loads(self.content),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
        return section_adapter.validate_python(data)

    @classmethod
    def from_pydantic(cls, schema: ResumeSectionSchema) -> ResumeSection:
        if schema.content is not None:
            content = json.dumps(schema.content.model_dump(), ensure_ascii=False)
        elif schema.type in {"personal_info", "summary", "custom"}:
            content = "{}"
        elif schema.type == "skills":
            content = '{"categories": []}'
        else:
            content = '{"items": []}'
        # 为 None 时使用当前时间，让 ORM 的 default/onupdate 生效
        created = schema.created_at or utc_now()
        updated = schema.updated_at or utc_now()
        return cls(
            id=schema.id,
            resume_id=schema.resume_id,
            title=schema.title,
            type=schema.type,
            sort_order=schema.sort_order,
            visible=schema.visible,
            content=content,
            created_at=created,
            updated_at=updated,
        )


class BaseWork(Base):
    """通用任务流数据库模型。"""

    __tablename__ = "work"
    __table_args__ = (
        Index("ix_work_task_status_updated", "task_type", "status", "updated_at"),
        Index("ix_work_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="任务唯一id")
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="任务类型标识"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=True, default="pending", comment="当前状态"
    )
    meta_info: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=dict, comment="任务元数据"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="更新时间",
    )


class ConversationMessageRecord(PydanticMixin, Base):
    """会话消息数据库模型"""

    __tablename__ = "conversation_messages"
    __table_args__ = (
        Index(
            "ix_conversation_messages_conversation_created",
            "conversation_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="消息唯一标识",
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="所属会话 ID",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="消息角色，user 或 assistant",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="消息内容，JSON 字符串",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        comment="创建时间",
    )

    def to_pydantic(self) -> ConversationMessageSchema:
        """转换为 Pydantic DTO"""
        return ConversationMessageSchema.model_validate(
            {
                "id": self.id,
                "conversation_id": self.conversation_id,
                "role": self.role,
                "content": json.loads(self.content) if self.content else [],
                "created_at": self.created_at,
            }
        )

    @classmethod
    def from_pydantic(
        cls, schema: ConversationMessageSchema
    ) -> ConversationMessageRecord:
        """从 Pydantic DTO 创建数据库模型"""
        return cls(
            id=schema.id,
            conversation_id=schema.conversation_id,
            role=schema.role,
            content=json.dumps(
                [block.model_dump(mode="json") for block in schema.content],
                ensure_ascii=False,
            ),
            created_at=schema.created_at,
        )


class UserConfig(Base):
    """用户配置数据库模型

    使用统一的 key-value 结构存储各类用户配置，
    支持灵活扩展配置项而无需修改表结构。
    """

    __tablename__ = "user_config"

    key: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        primary_key=True,
        comment="配置项标识",
    )
    value: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="配置值，JSON 对象",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="最后更新时间",
    )


class JobDescriptionAnalysis(PydanticMixin, Base):
    """职位描述分析数据库模型"""

    __tablename__ = "job_description_analysis"
    __table_args__ = (
        Index("ix_jd_analysis_resume_created", "resume_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="职位描述分析唯一标识",
    )
    resume_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resumes.id"),
        nullable=False,
        index=True,
        comment="职位描述分析所属简历 ID",
    )
    job_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="职位描述",
    )
    overall_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="职位描述分析总分(0-100)",
    )
    ats_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="职位描述分析ATS得分(0-100)",
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="职位描述分析总结",
    )
    keyword_matches: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="职位描述分析关键词匹配结果",
    )
    missing_keywords: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="职位描述分析缺少的关键词",
    )
    suggestions: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="职位描述分析建议",
    )
    partial_matches: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="职位描述分析部分匹配结果",
    )
    skill_matches: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="职位描述分析技能匹配结果",
    )
    strengths: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="职位描述分析核心strength",
    )
    jd_requirements: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="JD预提取结构化要求列表",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="创建时间",
    )

    resume = relationship("Resume", back_populates="job_description_analyses")

    def to_pydantic(self) -> JobDescriptionAnalysisSchema:
        suggestions = [
            SuggestionItem.model_validate(suggestion)
            for suggestion in json.loads(self.suggestions)
        ]
        keyword_matches = [
            KeywordMatchItem.model_validate(keyword_match)
            for keyword_match in json.loads(self.keyword_matches)
        ]
        missing_keywords = [
            KeywordMissingItem.model_validate(missing_keyword)
            for missing_keyword in json.loads(self.missing_keywords)
        ]
        partial_matches = [
            PartialMatchItem.model_validate(partial_match)
            for partial_match in json.loads(self.partial_matches)
        ]
        skill_matches = [
            SkillMatchItem.model_validate(skill_match)
            for skill_match in json.loads(self.skill_matches)
        ]
        strengths = [
            StrengthItem.model_validate(strength)
            for strength in json.loads(self.strengths)
        ]
        jd_requirements = [
            JdRequirementItem.model_validate(_drop_legacy_raw_text(req))
            for req in json.loads(self.jd_requirements)
        ]

        return JobDescriptionAnalysisSchema(
            id=self.id,
            resume_id=self.resume_id,
            job_description=self.job_description,
            overall_score=self.overall_score,
            ats_score=self.ats_score,
            summary=self.summary,
            keyword_matches=keyword_matches,
            missing_keywords=missing_keywords,
            suggestions=suggestions,
            partial_matches=partial_matches,
            skill_matches=skill_matches,
            strengths=strengths,
            jd_requirements=jd_requirements,
            created_at=self.created_at,
        )

    @classmethod
    def from_pydantic(
        cls, schema: JobDescriptionAnalysisSchema
    ) -> JobDescriptionAnalysis:
        suggestions = [suggestion.model_dump() for suggestion in schema.suggestions]
        keyword_matches = [
            keyword_match.model_dump() for keyword_match in schema.keyword_matches
        ]
        missing_keywords = [
            missing_keyword.model_dump() for missing_keyword in schema.missing_keywords
        ]
        partial_matches = [
            partial_match.model_dump() for partial_match in schema.partial_matches
        ]
        skill_matches = [
            skill_match.model_dump() for skill_match in schema.skill_matches
        ]
        strengths = [strength.model_dump() for strength in schema.strengths]
        jd_requirements = [req.model_dump() for req in schema.jd_requirements]
        return cls(
            resume_id=schema.resume_id,
            job_description=schema.job_description,
            overall_score=schema.overall_score,
            ats_score=schema.ats_score,
            summary=schema.summary,
            keyword_matches=json.dumps(keyword_matches, ensure_ascii=False),
            missing_keywords=json.dumps(missing_keywords, ensure_ascii=False),
            suggestions=json.dumps(suggestions, ensure_ascii=False),
            partial_matches=json.dumps(partial_matches, ensure_ascii=False),
            skill_matches=json.dumps(skill_matches, ensure_ascii=False),
            strengths=json.dumps(strengths, ensure_ascii=False),
            jd_requirements=json.dumps(jd_requirements, ensure_ascii=False),
        )


class JobDescriptionProfile(PydanticMixin, Base):
    """JD 结构化画像数据库模型。"""

    __tablename__ = "job_description_profiles"
    __table_args__ = (
        UniqueConstraint(
            "resume_id",
            "source_hash",
            "schema_version",
            name="uq_jd_profiles_resume_hash_schema",
        ),
        Index("ix_jd_profiles_resume_hash", "resume_id", "source_hash"),
        Index("ix_jd_profiles_resume_status", "resume_id", "status"),
        Index("ix_jd_profiles_status_updated", "status", "updated_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="JD Profile 唯一标识",
    )
    resume_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resumes.id"),
        nullable=False,
        index=True,
        comment="所属子简历 ID",
    )
    source_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="岗位名称与 JD 正文规范化后的哈希",
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="JD Profile 结构版本",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="queued",
        comment="解析状态",
    )
    profile_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
        comment="结构化 JD Profile JSON",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="最近一次解析失败原因",
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="解析尝试次数",
    )
    provider_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="最近一次解析使用的 Provider",
    )
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="最近一次解析使用的模型",
    )
    trigger: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="最近一次解析触发来源",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="更新时间",
    )

    resume = relationship("Resume", back_populates="job_description_profiles")

    def to_pydantic(self) -> JobDescriptionProfileSchema:
        profile: JdProfileData | None = None
        if self.profile_json and self.profile_json != "{}":
            profile = JdProfileData.model_validate(
                _drop_legacy_raw_text(json.loads(self.profile_json))
            )
        return JobDescriptionProfileSchema(
            id=self.id,
            resume_id=self.resume_id,
            source_hash=self.source_hash,
            schema_version=self.schema_version,
            status=self.status,
            profile=profile,
            error_message=self.error_message,
            attempts=self.attempts,
            provider_type=self.provider_type,
            model=self.model,
            trigger=self.trigger,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_pydantic(
        cls, schema: JobDescriptionProfileSchema
    ) -> JobDescriptionProfile:
        return cls(
            resume_id=schema.resume_id,
            source_hash=schema.source_hash,
            schema_version=schema.schema_version,
            status=schema.status,
            profile_json=(
                schema.profile.model_dump_json() if schema.profile is not None else "{}"
            ),
            error_message=schema.error_message,
            attempts=schema.attempts,
            provider_type=schema.provider_type,
            model=schema.model,
            trigger=schema.trigger,
            created_at=schema.created_at or utc_now(),
            updated_at=schema.updated_at or utc_now(),
        )


class GreetingGenerationBatch(PydanticMixin, Base):
    """已持久化的一批结构化招呼语候选。"""

    __tablename__ = "greeting_generation_batches"
    __table_args__ = (
        Index("ix_greeting_batches_resume_created", "resume_id", "created_at"),
        Index("ix_greeting_batches_resume_status", "resume_id", "status"),
        Index("ix_greeting_batches_source_hash", "resume_id", "source_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id"), nullable=False
    )
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resume_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    user_edits_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    selected_style: Mapped[str | None] = mapped_column(String(30), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    resume = relationship("Resume", back_populates="greeting_batches")

    def to_pydantic(self) -> GreetingBatchSchema:
        result = None
        if self.result_json and self.result_json != "{}":
            result = GreetingGenerationResult.model_validate(
                json.loads(self.result_json)
            )
        return GreetingBatchSchema(
            id=self.id,
            resume_id=self.resume_id,
            workspace_id=self.workspace_id,
            source_hash=self.source_hash,
            resume_content_hash=self.resume_content_hash,
            schema_version=self.schema_version,
            status=self.status,
            result=result,
            user_edits=json.loads(self.user_edits_json or "{}"),
            selected_style=self.selected_style,
            error_message=self.error_message,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class CoverLetterGenerationBatch(PydanticMixin, Base):
    """已持久化的一次求职信生成结果。"""

    __tablename__ = "cover_letter_generation_batches"
    __table_args__ = (
        Index("ix_cover_letters_resume_created", "resume_id", "created_at"),
        Index("ix_cover_letters_resume_status", "resume_id", "status"),
        Index("ix_cover_letters_source_hash", "resume_id", "source_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id"), nullable=False
    )
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resume_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    params_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    generated_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    resume = relationship("Resume", back_populates="cover_letter_batches")

    def to_pydantic(self) -> CoverLetterBatchSchema:
        return CoverLetterBatchSchema(
            id=self.id,
            resume_id=self.resume_id,
            workspace_id=self.workspace_id,
            source_hash=self.source_hash,
            resume_content_hash=self.resume_content_hash,
            profile_id=self.profile_id,
            profile_schema_version=self.profile_schema_version,
            status=self.status,
            params=CoverLetterGenerationParams.model_validate(
                json.loads(self.params_json or "{}")
            ),
            generated_content=self.generated_content,
            edited_content=self.edited_content,
            error_message=self.error_message,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class InterviewCollection(PydanticMixin, Base):
    """面试集合体数据库模型"""

    __tablename__ = "interview_collections"
    __table_args__ = (
        Index("ix_interview_collections_resume_created", "sub_resume_id", "created_at"),
        Index("ix_interview_collections_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="面试集合唯一标识",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="面试集合名称",
    )
    sub_resume_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resumes.id"),
        nullable=False,
        index=True,
        comment="关联的子简历ID",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="not_started",
        comment="状态：not_started/in_progress/completed",
    )
    meta_info: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="集合元数据，包含总体面试总结等",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="更新时间",
    )

    resume = relationship(
        "Resume",
        back_populates="interview_collections",
        foreign_keys=[sub_resume_id],
    )
    rounds = relationship(
        "InterviewRound",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="InterviewRound.sort_order",
    )

    def to_pydantic(self) -> InterviewCollectionSchema:
        """转换为 Pydantic DTO"""
        return InterviewCollectionSchema(
            id=self.id,
            name=self.name,
            sub_resume_id=self.sub_resume_id,
            status=self.status,
            meta_info=self.meta_info,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_pydantic(cls, schema: InterviewCollectionSchema) -> InterviewCollection:
        """从 Pydantic DTO 创建数据库模型"""
        created = schema.created_at or utc_now()
        updated = schema.updated_at or utc_now()
        return cls(
            id=schema.id,
            name=schema.name,
            sub_resume_id=schema.sub_resume_id,
            status=schema.status,
            meta_info=schema.meta_info,
            created_at=created,
            updated_at=updated,
        )


class InterviewRound(PydanticMixin, Base):
    """面试轮次数据库模型"""

    __tablename__ = "interview_rounds"
    __table_args__ = (
        Index(
            "ix_interview_rounds_collection_sort",
            "interview_collection_id",
            "sort_order",
        ),
        Index(
            "ix_interview_rounds_collection_status",
            "interview_collection_id",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="面试轮次ID，同时也是会话ID",
    )
    interview_collection_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interview_collections.id"),
        nullable=False,
        index=True,
        comment="所属面试集合ID",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="轮次名称，如'技术一面'",
    )
    interviewer_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="面试官名称",
    )
    interviewer_title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="",
        comment="面试官头衔",
    )
    interviewer_bio: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="面试官简介",
    )
    question_style: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="",
        comment="提问风格",
    )
    assessment_dimensions: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="考察维度，JSON数组字符串",
    )
    personality_traits: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="性格特征，JSON数组字符串",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="not_started",
        comment="状态：not_started/in_progress/completed",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="排序序号",
    )
    meta_info: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="轮次元数据，包含面试摘要等",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="更新时间",
    )

    collection = relationship("InterviewCollection", back_populates="rounds")

    def to_pydantic(self) -> InterviewRoundSchema:
        """转换为 Pydantic DTO"""
        return InterviewRoundSchema(
            id=self.id,
            interview_collection_id=self.interview_collection_id,
            name=self.name,
            interviewer_name=self.interviewer_name,
            interviewer_title=self.interviewer_title,
            interviewer_bio=self.interviewer_bio,
            question_style=self.question_style,
            assessment_dimensions=json.loads(self.assessment_dimensions),
            personality_traits=json.loads(self.personality_traits),
            status=self.status,
            sort_order=self.sort_order,
            meta_info=self.meta_info,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_pydantic(cls, schema: InterviewRoundSchema) -> InterviewRound:
        """从 Pydantic DTO 创建数据库模型"""
        created = schema.created_at or utc_now()
        updated = schema.updated_at or utc_now()
        return cls(
            id=schema.id,
            interview_collection_id=schema.interview_collection_id,
            name=schema.name,
            interviewer_name=schema.interviewer_name,
            interviewer_title=schema.interviewer_title,
            interviewer_bio=schema.interviewer_bio,
            question_style=schema.question_style,
            assessment_dimensions=json.dumps(
                schema.assessment_dimensions, ensure_ascii=False
            ),
            personality_traits=json.dumps(
                schema.personality_traits, ensure_ascii=False
            ),
            status=schema.status,
            sort_order=schema.sort_order,
            meta_info=schema.meta_info,
            created_at=created,
            updated_at=updated,
        )
