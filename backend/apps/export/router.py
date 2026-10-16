"""导出路由，提供 PDF / TXT / JSON 导出接口"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.export.pdf_generator import generate_pdf
from apps.export.service import export_json, export_txt
from chiren_backend.platform.db import get_session


class ExportPdfRequest(BaseModel):
    """PDF 导出请求体"""

    html: str = Field(description="待渲染的 HTML 内容")
    timeout_ms: int = Field(default=30000, description="超时时间（毫秒）")


router = APIRouter(prefix="/export", tags=["export"])


@router.post("/pdf", summary="导出 PDF")
async def export_pdf(request: ExportPdfRequest) -> Response:
    """根据 HTML 内容生成并返回 PDF 文件。

    Args:
        request: 包含 HTML 内容和可选超时配置。

    Returns:
        PDF 文件流。

    Raises:
        HTTPException: HTML 内容为空时抛出 422。
    """
    if not request.html.strip():
        raise HTTPException(status_code=422, detail="HTML内容不能为空")

    pdf_bytes = await generate_pdf(request.html, request.timeout_ms)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resume.pdf"},
    )


@router.get("/txt/{resume_id}", summary="导出 TXT")
async def export_txt_endpoint(
    resume_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """根据简历 ID 导出纯文本格式简历。

    Args:
        resume_id: 简历唯一标识。
        db: 数据库会话。

    Returns:
        TXT 文件流。

    Raises:
        HTTPException: 简历不存在时抛出 404。
    """
    try:
        text = await export_txt(resume_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="简历不存在") from exc

    return Response(
        content=text.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=resume.txt"},
    )


@router.get("/json/{resume_id}", summary="导出 JSON")
async def export_json_endpoint(
    resume_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """根据简历 ID 导出 JSON 格式简历。

    Args:
        resume_id: 简历唯一标识。
        db: 数据库会话。

    Returns:
        JSON 文件流。

    Raises:
        HTTPException: 简历不存在时抛出 404。
    """
    try:
        data = await export_json(resume_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="简历不存在") from exc

    return JSONResponse(
        content=jsonable_encoder(data),
        headers={"Content-Disposition": "attachment; filename=resume.json"},
    )
