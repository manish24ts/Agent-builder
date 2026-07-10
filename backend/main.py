"""main.py — FastAPI application entrypoint.

Run with:  uvicorn backend.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.agent_routes import router as agent_router
from backend.api.auth_routes import router as auth_router
from backend.api.chat_routes import router as chat_router
from backend.api.conversation_routes import router as conversation_router
from backend.core.config import FRONTEND_ORIGIN_REGEX, FRONTEND_ORIGINS

app = FastAPI(title="Agent Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=FRONTEND_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(conversation_router)
app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
