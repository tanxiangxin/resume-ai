"""简历路由的请求/响应 schema 定义

该模块封装了简历 API 的请求体和响应体类型，
与 shared/types/resume.py 中的通用模型区分开，
专注于路由层的输入输出契约。
"""

from pydantic import BaseModel, ConfigDict, Field, alias_generators


class CreateWorkspaceRequest(BaseModel):
    """创建 Workspace（主简历）的请求体"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    title: str = Field(default="未命名简历", description="简历标题")
    theme_config: dict = Field(default_factory=dict, description="主题配置")
    template: str = Field(default="classic", description="模板名称")
    language: str = Field(default="zh", description="简历语言")


class CreateSubResumeRequest(BaseModel):
    """创建子简历的请求体"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    workspace_id: str = Field(description="所属 Workspace ID")
    job_description: str = Field(description="职位描述")
    title: str = Field(default="未命名简历", description="简历标题")
    job_title: str | None = Field(default=None, description="目标职位")
    theme_config: dict = Field(default_factory=dict, description="主题配置")
    template: str = Field(default="classic", description="模板名称")
    language: str = Field(default="zh", description="简历语言")
