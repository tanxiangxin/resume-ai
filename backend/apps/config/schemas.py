"""Config Pydantic 模型。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, alias_generators

LLM_PROVIDERS = Literal["openai", "anthropic"]


class ProviderConfigItem(BaseModel):
    """单个 Provider 配置项"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    base_url: str = Field(default="", description="API 地址")
    api_key: str = Field(default="", description="API 密钥")
    model: str = Field(default="", description="模型名称")


class ProviderConfig(BaseModel):
    """Provider 配置完整结构"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    providers: dict[str, ProviderConfigItem] = Field(
        default_factory=dict,
        description="所有 provider 配置，key 为 provider 类型",
    )
    active: LLM_PROVIDERS = Field(
        default="openai", description="当前激活的 provider 类型"
    )


class ProviderConfigUpdate(BaseModel):
    """更新 provider 配置的请求模型"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    type: LLM_PROVIDERS = Field(description="Provider 类型，openai 或 anthropic")
    base_url: str | None = Field(default=None, description="API 地址")
    api_key: str | None = Field(default=None, description="API 密钥")
    model: str | None = Field(default=None, description="模型名称")


class ProviderSwitch(BaseModel):
    """切换激活 provider 的请求模型"""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    active: LLM_PROVIDERS = Field(description="要激活的 provider 类型")
