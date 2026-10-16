import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from chiren_backend.platform.db import get_session
from chiren_backend.platform.models import ResumeSection
from shared.types.resume import ResumeSectionSchema

log = logging.getLogger(__name__)

router = APIRouter(prefix="/resume-section", tags=["resume-section"])


@router.get(
    "/one",
    summary="根据区块Id获取区块",
)
async def get_by_id_and_type(
    id: Annotated[str, Query(description="区块ID")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ResumeSectionSchema:
    result = await db.execute(select(ResumeSection).where(ResumeSection.id == id))
    resume_section = result.scalar_one_or_none()
    if not resume_section:
        raise HTTPException(status_code=404, detail="数据不存在")
    return resume_section.to_pydantic()


@router.get(
    "/{id}",
    summary="根据简历id获取区块列表",
)
async def get_by_resumeid(
    id: Annotated[str, Path(description="简历ID")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[ResumeSectionSchema]:
    result = await db.execute(
        select(ResumeSection)
        .where(ResumeSection.resume_id == id)
        .order_by(ResumeSection.sort_order.asc(), ResumeSection.id.asc())
    )
    resume_section_list = result.scalars().all()
    return [item.to_pydantic() for item in resume_section_list]


@router.post("/create", summary="添加区块")
async def create_section(
    data: ResumeSectionSchema,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ResumeSectionSchema:

    section = ResumeSection.from_pydantic(data)
    db.add(section)
    try:
        await db.commit()
        await db.refresh(section)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="新增失败")
    return section.to_pydantic()


@router.put("/update", summary="修改区块，不存在时自动创建")
async def update_section(
    data: ResumeSectionSchema,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ResumeSectionSchema:
    result = await db.execute(select(ResumeSection).where(ResumeSection.id == data.id))
    resume_section = result.scalar_one_or_none()

    if resume_section is None:
        # 不存在则创建（upsert）
        section = ResumeSection.from_pydantic(data)
        db.add(section)
        try:
            await db.commit()
            await db.refresh(section)
        except Exception:
            await db.rollback()
            raise HTTPException(status_code=500, detail="新增失败")
        return section.to_pydantic()

    updates = data.model_dump(exclude_unset=True)
    # content 字段做 shallow merge，避免部分更新丢失未发送的字段
    if "content" in updates and updates["content"]:
        existing_content = json.loads(resume_section.content)
        if isinstance(existing_content, dict):
            merged = {**existing_content, **updates["content"]}
            updates["content"] = json.dumps(merged, ensure_ascii=False)
        else:
            updates["content"] = json.dumps(updates["content"], ensure_ascii=False)
    for key, value in updates.items():
        setattr(resume_section, key, value)
    try:
        await db.commit()
        await db.refresh(resume_section)
    except Exception as e:
        await db.rollback()
        log.error("更新区块失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"修改失败: {str(e)}")
    return resume_section.to_pydantic()


@router.delete("/delete", summary="删除指定区块")
async def delete_section(
    id: Annotated[str, Query(description="区块ID")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    await db.execute(delete(ResumeSection).where(ResumeSection.id == id))
    try:
        await db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="删除失败")
    return None


@router.delete("/delete/all", summary="清除指定简历所有区块")
async def delete_all(
    id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    await db.execute(delete(ResumeSection).where(ResumeSection.resume_id == id))
    try:
        await db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="删除失败")
    return None
