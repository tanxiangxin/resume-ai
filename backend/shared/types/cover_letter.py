from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from shared.types.strict_model import StrictBaseModel

CoverLetterStyle = Literal["正式", "亲切", "自信"]
CoverLetterLanguage = Literal["中文", "English"]
CoverLetterLength = Literal["short", "standard"]
CoverLetterBatchStatus = Literal["pending", "running", "success", "error", "obsolete"]


class CoverLetterGenerationParams(StrictBaseModel):
    style: CoverLetterStyle = "正式"
    language: CoverLetterLanguage = "中文"
    length: CoverLetterLength = "standard"
    company_name: str | None = Field(default=None, max_length=200)
    recipient_name: str | None = Field(default=None, max_length=100)
    additional_instructions: str | None = Field(default=None, max_length=2000)


class CoverLetterBatchSchema(StrictBaseModel):
    id: str
    resume_id: str
    workspace_id: str | None = None
    source_hash: str
    resume_content_hash: str
    profile_id: int | None = None
    profile_schema_version: int
    status: CoverLetterBatchStatus
    params: CoverLetterGenerationParams
    generated_content: str | None = None
    edited_content: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
