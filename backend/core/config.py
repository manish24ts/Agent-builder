"""config.py — central app settings, loaded once from backend/.env."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "10080"))  # 7 days

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

# Comma-separated list of exact origins allowed to call the API, e.g.
# "http://localhost:5173,https://agent-builder.vercel.app"
FRONTEND_ORIGINS = [o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173").split(",") if o.strip()]

# Optional regex to additionally allow, e.g. Vercel preview deployments:
# "https://agent-builder-.*\.vercel\.app"
FRONTEND_ORIGIN_REGEX = os.environ.get("FRONTEND_ORIGIN_REGEX", "")

DB_SSL_REQUIRE = os.environ.get("DB_SSL_REQUIRE", "false").lower() == "true"


def get_database_url() -> str:
    """
    Reads DATABASE_URL and normalizes it to the asyncpg driver form.
    Render (and most managed Postgres hosts) hand you `postgres://...` or
    `postgresql://...` — SQLAlchemy's async engine needs `postgresql+asyncpg://...`.
    """
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url
