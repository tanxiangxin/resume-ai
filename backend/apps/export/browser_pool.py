"""Playwright 浏览器连接池管理模块。

提供常驻 Chromium 实例的连接池，避免每次 PDF 生成都启动新浏览器。
支持延迟加载、自动回收空闲连接、以及优雅关闭。
"""

import asyncio
import contextlib
import logging
import time

from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import async_playwright

log = logging.getLogger(__name__)

# 默认配置
DEFAULT_IDLE_TIMEOUT = 300  # 空闲超时时间（秒）
DEFAULT_CHECK_INTERVAL = 60  # 检查间隔（秒）


class BrowserPool:
    """Playwright 浏览器连接池。

    实现延迟加载：首次请求时启动浏览器，后续请求复用。
    支持自动回收空闲实例，避免内存泄漏。

    Attributes:
        _browser: 浏览器实例
        _playwright: Playwright 上下文管理器
        _lock: 并发锁，确保浏览器初始化的线程安全
        _last_used: 最后使用时间戳
        _idle_timeout: 空闲超时时间（秒）
        _shutdown_task: 自动关闭任务
    """

    def __init__(self, idle_timeout: int = DEFAULT_IDLE_TIMEOUT):
        """初始化浏览器池。

        Args:
            idle_timeout: 空闲超时时间（秒），超过此时间无请求将自动关闭浏览器。
        """
        self._browser: PlaywrightBrowser | None = None
        self._playwright = None
        self._lock = asyncio.Lock()
        self._last_used: float = 0
        self._idle_timeout = idle_timeout
        self._shutdown_task: asyncio.Task | None = None

    async def get_browser(self) -> PlaywrightBrowser:
        """获取浏览器实例，如果未启动则延迟初始化。

        Returns:
            已启动的浏览器实例。

        Raises:
            RuntimeError: 浏览器启动失败时抛出。
        """
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                await self._start_browser()
            self._last_used = time.time()
            return self._browser

    async def _start_browser(self) -> None:
        """启动浏览器实例（内部方法）。

        使用 Playwright 的 BrowserServer 模式启动长期运行的浏览器。
        """
        # 如果有旧的实例，先关闭
        if self._browser is not None:
            with contextlib.suppress(Exception):
                await self._browser.close()

        # 启动新的 Playwright 上下文
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        log.info("浏览器实例已启动（延迟加载）")

        # 启动自动关闭检查
        self._schedule_shutdown()

    def _schedule_shutdown(self) -> None:
        """调度自动关闭任务。

        如果已有任务在运行，先取消再重新调度。
        """
        if self._shutdown_task and not self._shutdown_task.done():
            self._shutdown_task.cancel()
        self._shutdown_task = asyncio.create_task(self._auto_shutdown())

    async def _auto_shutdown(self) -> None:
        """自动关闭空闲浏览器。

        定期检查最后使用时间，如果超过阈值则关闭浏览器释放资源。
        """
        try:
            while True:
                await asyncio.sleep(DEFAULT_CHECK_INTERVAL)
                if time.time() - self._last_used > self._idle_timeout:
                    await self.close()
                    log.info("浏览器因空闲超时已自动关闭")
                    break
        except asyncio.CancelledError:
            pass  # 任务被取消，正常退出

    async def close(self) -> None:
        """关闭浏览器实例和 Playwright 上下文。

        释放所有资源，可以在应用关闭时调用。
        """
        if self._shutdown_task and not self._shutdown_task.done():
            self._shutdown_task.cancel()
            self._shutdown_task = None

        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
            log.info("浏览器实例已关闭")

        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None


# 全局浏览器池实例（延迟初始化）
_browser_pool: BrowserPool | None = None


def get_browser_pool() -> BrowserPool:
    """获取全局浏览器池实例。

    Returns:
        全局浏览器池实例（单例）。
    """
    global _browser_pool
    if _browser_pool is None:
        _browser_pool = BrowserPool()
    return _browser_pool


async def close_browser_pool() -> None:
    """关闭全局浏览器池。

    应在应用关闭时调用，释放所有资源。
    """
    global _browser_pool
    if _browser_pool is not None:
        await _browser_pool.close()
        _browser_pool = None
