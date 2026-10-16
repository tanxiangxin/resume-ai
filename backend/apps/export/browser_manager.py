"""Playwright 浏览器管理模块。

提供后台异步安装 Chromium 的能力，并在安装完成前通过 Event 机制
让 PDF 生成接口快速失败，避免请求长时间阻塞。
"""

import asyncio
import logging

from fastapi import HTTPException
from playwright.async_api import async_playwright

log = logging.getLogger(__name__)

_browser_ready = asyncio.Event()
_install_lock = asyncio.Lock()


async def is_browser_installed() -> bool:
    """检测 Chromium 浏览器是否已安装。

    Returns:
        如果 Playwright 能找到可执行的 Chromium 路径则返回 True。
    """
    try:
        async with async_playwright() as p:
            return p.chromium.executable_path is not None
    except Exception:
        return False


async def ensure_browser() -> None:
    """确保 Chromium 浏览器可用，必要时在后台异步安装。

    该函数是幂等的：重复调用不会触发多次安装。
    安装完成后会设置内部 Event，使 ``check_browser_ready`` 放行。
    """
    async with _install_lock:
        if _browser_ready.is_set():
            return

        if await is_browser_installed():
            _browser_ready.set()
            log.info("Chromium is already installed")
            return

        log.info("Chromium not found, installing in background...")
        proc = await asyncio.create_subprocess_exec(
            "python",
            "-m",
            "playwright",
            "install",
            "chromium",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            log.info("Chromium installed successfully")
            _browser_ready.set()
        else:
            err_msg = (
                stderr.decode().strip() or stdout.decode().strip() or "unknown error"
            )
            log.error("Chromium installation failed: %s", err_msg)


def check_browser_ready() -> None:
    """检查浏览器是否已就绪，未就绪时抛出 503 快速失败。

    Raises:
        HTTPException: 503 Service Unavailable，提示浏览器正在初始化。
    """
    if not _browser_ready.is_set():
        raise HTTPException(
            status_code=503,
            detail="PDF 服务初始化中，浏览器内核尚未就绪，请稍后重试",
        )
