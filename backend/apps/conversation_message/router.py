"""会话消息管理路由。"""

import json
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, alias_generators
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from chiren_backend.platform.db import get_session
from chiren_backend.platform.models import ConversationMessageRecord
from shared.types.messages import ConversationMessageSchema

router = APIRouter(prefix="/conversation-message", tags=["conversation-message"])


class CreateMessageRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    conversation_id: str
    user_input: str


@router.get("/list/{conversation_id}", summary="获取会话消息列表")
async def get_message_list(
    conversation_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[ConversationMessageSchema]:
    stmt = (
        select(ConversationMessageRecord)
        .where(ConversationMessageRecord.conversation_id == conversation_id)
        .order_by(ConversationMessageRecord.created_at)
    )
    result = await db.execute(stmt)
    record_list = result.scalars().all()
    return [record.to_pydantic() for record in record_list]


@router.post("/create", summary="创建用户消息")
async def create_message(
    request: Annotated[CreateMessageRequest, Body()],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationMessageSchema:
    record = ConversationMessageRecord(
        conversation_id=request.conversation_id,
        role="user",
        content=json.dumps(
            [{"type": "text", "text": request.user_input}], ensure_ascii=False
        ),
    )
    db.add(record)
    try:
        await db.commit()
        await db.refresh(record)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="创建失败")
    return record.to_pydantic()


@router.delete("/delete", summary="根据id删除消息")
async def delete_message(
    id: Annotated[int, Query(description="消息ID")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    await db.execute(
        delete(ConversationMessageRecord).where(ConversationMessageRecord.id == id)
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="删除失败")
    return None


@router.delete("/delete/conversation", summary="根据会话id删除消息")
async def delete_message_by_conversation_id(
    conversation_id: Annotated[str, Query(description="会话ID")],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    await db.execute(
        delete(ConversationMessageRecord).where(
            ConversationMessageRecord.conversation_id == conversation_id
        )
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="删除失败")
    return None
