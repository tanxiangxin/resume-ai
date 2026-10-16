from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from shared.types.strict_model import StrictBaseModel

GREETING_SCHEMA_VERSION = 1
GreetingStyle = Literal["professional", "natural", "match_focused"]
GreetingBatchStatus = Literal["pending", "running", "success", "error", "obsolete"]


class GreetingMatchPoint(StrictBaseModel):
    requirement_id: str = Field(
        description=(
            "An id from JD Profile requirements[].id only; never use a "
            "core_selection_criteria[].id here"
        )
    )
    evidence: str = Field(
        min_length=1,
        description="Resume-grounded evidence, which may be naturally paraphrased",
    )


class GreetingVariant(StrictBaseModel):
    style: GreetingStyle
    text: str = Field(min_length=1)
    match_points: list[GreetingMatchPoint] = Field(min_length=1, max_length=2)
    selection_criterion_id: str | None = Field(
        default=None,
        description=(
            "An id from JD Profile core_selection_criteria[].id only; this is "
            "separate from match_points[].requirement_id"
        ),
    )


class GreetingGenerationResult(StrictBaseModel):
    schema_version: int = GREETING_SCHEMA_VERSION
    variants: list[GreetingVariant] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_variants(self) -> GreetingGenerationResult:
        styles = [variant.style for variant in self.variants]
        if len(set(styles)) != 3:
            raise ValueError("Greeting variants must use three unique styles")
        texts = [variant.text.strip() for variant in self.variants]
        if len(set(texts)) != 3:
            raise ValueError("Greeting variants must have unique text")
        return self


class GreetingBatchSchema(StrictBaseModel):
    id: str
    resume_id: str
    workspace_id: str | None = None
    source_hash: str
    resume_content_hash: str
    schema_version: int = GREETING_SCHEMA_VERSION
    status: GreetingBatchStatus
    result: GreetingGenerationResult | None = None
    user_edits: dict[str, str] = Field(default_factory=dict)
    selected_style: GreetingStyle | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GreetingGenerateResponse(StrictBaseModel):
    task_id: str
    batch_id: str
