"""chat_routes.py — Chat endpoint wiring the agent + streaming + persistence together."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.agent.stream import stream_agent_response
from backend.api.deps import get_current_user
from backend.db.database import get_db_session
from backend.db.models import Conversation, User

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    conversation_id: UUID
    message: str


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages), selectinload(Conversation.agent))
        .where(Conversation.id == payload.conversation_id, Conversation.user_id == current_user.id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(404, "Conversation not found.")

    # Auto-title a brand-new conversation from the first message.
    if conversation.title == "New Conversation" and not conversation.messages:
        conversation.title = payload.message.strip()[:60] or "New Conversation"
        await db.commit()

    return StreamingResponse(
        stream_agent_response(db, conversation.agent, conversation, payload.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
