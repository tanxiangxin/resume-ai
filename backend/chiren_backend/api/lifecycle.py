"""应用启动和关闭生命周期。"""

import asyncio
import logging
from types import TracebackType

from fastapi import FastAPI

from apps.export.browser_manager import ensure_browser
from apps.export.browser_pool import close_browser_pool
from apps.work import cleanup_work
from chiren_backend.platform.db import init_db

log = logging.getLogger(__name__)


class AppLifespan:
    """FastAPI 应用生命周期管理器。"""

    async def __aenter__(self) -> None:
        await startup_runtime()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await shutdown_runtime()


def create_lifespan(_app: FastAPI) -> AppLifespan:
    """创建 FastAPI 生命周期管理器。"""
    return AppLifespan()


async def startup_runtime() -> None:
    """初始化运行时资源。"""
    await init_db()
    deleted = await cleanup_work()
    log.info("Cleaned up %d work records on startup", deleted)
    asyncio.create_task(ensure_browser())


async def shutdown_runtime() -> None:
    """释放运行时资源。"""
    await close_browser_pool()
