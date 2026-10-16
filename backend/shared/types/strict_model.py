from pydantic import BaseModel, ConfigDict, alias_generators


class StrictBaseModel(BaseModel):
    """禁止额外字段 + 自动 snake_case / camelCase 双向转换。"""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )
