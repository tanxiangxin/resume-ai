"""Config 路由定义。"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.config.schemas import (
    ProviderConfig,
    ProviderConfigUpdate,
    ProviderSwitch,
)
from apps.jd_profile.service import queue_profiles_after_provider_update
from chiren_backend.platform.db import get_session
from chiren_backend.platform.models import UserConfig

router = APIRouter(prefix="/config", tags=["config"])

PROVIDER_CONFIG_KEY = "provider_config"


async def _get_provider_config_from_db(
    db: AsyncSession,
) -> ProviderConfig:
    """从数据库获取 provider 配置。"""
    result = await db.execute(
        select(UserConfig).where(UserConfig.key == PROVIDER_CONFIG_KEY)
    )
    row = result.scalar_one_or_none()
    if not row:
        return ProviderConfig()
    return ProviderConfig.model_validate(row.value)


async def _save_provider_config(
    db: AsyncSession,
    config: ProviderConfig,
) -> None:
    """保存 provider 配置到数据库。"""
    result = await db.execute(
        select(UserConfig).where(UserConfig.key == PROVIDER_CONFIG_KEY)
    )
    row = result.scalar_one_or_none()
    if row:
        row.value = config.model_dump()
    else:
        db.add(UserConfig(key=PROVIDER_CONFIG_KEY, value=config.model_dump()))
    await db.commit()


@router.get(
    "/provider",
    summary="获取 Provider 配置",
)
async def get_provider_config(
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderConfig:
    """获取当前的 provider 配置。"""
    return await _get_provider_config_from_db(db)


@router.put(
    "/provider",
    summary="更新 Provider 配置",
)
async def update_provider_config(
    update: ProviderConfigUpdate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderConfig:
    """更新指定 provider 类型的配置。"""

    config = await _get_provider_config_from_db(db)

    if update.type not in config.providers:
        from apps.config.schemas import ProviderConfigItem

        config.providers[update.type] = ProviderConfigItem()

    provider = config.providers[update.type]
    if update.base_url is not None:
        provider.base_url = update.base_url
    if update.api_key is not None:
        provider.api_key = update.api_key
    if update.model is not None:
        provider.model = update.model

    await _save_provider_config(db, config)
    await queue_profiles_after_provider_update(
        db, background_tasks, trigger="provider_update"
    )
    return config


@router.patch(
    "/provider/switch",
    summary="切换激活的 Provider",
)
async def switch_provider(
    switch: ProviderSwitch,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderConfig:
    """切换当前激活的 provider 类型。"""

    config = await _get_provider_config_from_db(db)

    # 如果 provider 不存在，自动用空配置创建
    if switch.active not in config.providers:
        from apps.config.schemas import ProviderConfigItem

        config.providers[switch.active] = ProviderConfigItem()

    config.active = switch.active
    await _save_provider_config(db, config)
    await queue_profiles_after_provider_update(
        db, background_tasks, trigger="provider_switch"
    )
    return config
