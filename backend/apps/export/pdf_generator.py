"""
使用 Playwright 的 PDF 生成器（异步）。

本模块提供了一个异步函数，用于使用 Chromium（通过 Playwright）将 HTML 内容渲染为 PDF。
使用浏览器连接池复用实例，避免每次请求都启动新浏览器，显著提升性能。
"""

import asyncio
import contextlib

from apps.export.browser_manager import check_browser_ready
from apps.export.browser_pool import get_browser_pool


async def generate_pdf(html_content: str, timeout_ms: int = 30000) -> bytes:
    """使用 Playwright 将 HTML 内容生成为 PDF。

    从浏览器连接池获取实例，创建独立的 Page 上下文渲染 PDF。
    每次请求使用独立的 Page，确保并发安全。

    Args:
        html_content: 要渲染为 PDF 的 HTML 内容。
        timeout_ms: 操作允许的最大时间（毫秒）。
                    超时后将抛出 asyncio.TimeoutError。
    Returns:
        生成的 PDF 作为字节对象。
    """
    check_browser_ready()
    coro = _generate_pdf_internal(html_content)
    pdf_bytes = await asyncio.wait_for(coro, timeout=timeout_ms / 1000.0)
    return pdf_bytes


async def _generate_pdf_internal(html_content: str) -> bytes:
    """内部 PDF 生成逻辑。

    从连接池获取浏览器，创建独立的 Page 进行渲染。
    """
    pool = get_browser_pool()
    browser = await pool.get_browser()
    page = None
    try:
        page = await browser.new_page()
        # 设置视口为 A4 大致的 CSS 像素尺寸
        await page.set_viewport_size({"width": 794, "height": 1123})
        await page.set_content(html_content, wait_until="networkidle")
        # 等待字体就绪
        await page.evaluate("document.fonts.ready")
        # 小延迟以确保字体渲染（特别是 CJK 字体）
        await asyncio.sleep(0.2)
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        return pdf_bytes
    finally:
        if page is not None:
            with contextlib.suppress(Exception):
                await page.close()
