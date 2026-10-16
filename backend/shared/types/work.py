"""Work 相关 API 类型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, alias_generators


class WorkSchema(BaseModel):
    """工作任务 API 类型。对应 work 表的 Pydantic 映射。"""

    id: str = Field(default="", description="任务ID")
    task_type: str = Field(default="", description="任务类型标识")
    status: str = Field(default="", description="任务状态")
    meta_info: dict | None = Field(default=None, description="任务元数据")
    error_message: str | None = Field(default=None, description="错误信息")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )


class TaskIdResponse(BaseModel):
    """任务 ID 响应模型。"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    task_id: str
