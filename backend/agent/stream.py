from __future__ import annotations

import json
from typing import AsyncGenerator, List
from uuid import UUID

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.graph import build_agent_graph
from backend.db.models import Agent, Conversation, Message


def _load_history_as_messages(db_messages: List[Message]) -> List[AnyMessage]:
    """Reconstruct LangChain message objects from stored DB rows."""
    converted: List[AnyMessage] = []
    for m in db_messages:
        if m.role == "user":
            converted.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            converted.append(AIMessage(content=m.content))
        # tool messages are intentionally not replayed — they're an implementation
        # detail of a completed turn, not needed for the model to continue the conversation
    return converted


async def stream_agent_response(
    db: AsyncSession,
    agent: Agent,
    conversation: Conversation,
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Runs the agent for one user turn, yielding SSE-formatted chunks as the model
    streams tokens. Persists the user message immediately and the final assistant
    message once streaming completes, so a dropped connection mid-stream doesn't
    leave the DB in an inconsistent state (user turn is saved either way; assistant
    turn is only saved on successful completion).
    """
    try:
        graph = build_agent_graph(
            system_prompt=agent.system_prompt,
            tool_names=agent.tool_names,
            model=agent.model,
            temperature=agent.temperature,
        )
    except RuntimeError as exc:
        yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
        return

    db.add(Message(conversation_id=conversation.id, role="user", content=user_message))
    await db.commit()

    history = _load_history_as_messages(conversation.messages)
    input_messages = [*history, HumanMessage(content=user_message)]

    full_response = ""
    try:
        async for event in graph.astream_events({"messages": input_messages}, version="v2"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                token = chunk.content if isinstance(chunk.content, str) else ""
                if token:
                    full_response += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            elif kind == "on_tool_start":
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['name']})}\n\n"

            elif kind == "on_tool_end":
                yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['name']})}\n\n"

        db.add(Message(conversation_id=conversation.id, role="assistant", content=full_response))
        await db.commit()

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as exc:  # noqa: BLE001 — never let a streaming failure crash the connection silently
        yield f"data: {json.dumps({'type': 'error', 'error': f'Agent run failed: {exc}'})}\n\n"