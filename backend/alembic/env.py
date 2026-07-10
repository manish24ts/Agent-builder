"""Alembic environment — async engine, reads DATABASE_URL from .env, autogenerates from Base.metadata."""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

# Make `backend.*` importable when Alembic runs from the project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.db.models import Base  # noqa: E402 — import after sys.path fix
from backend.core.config import DB_SSL_REQUIRE, get_database_url  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

DATABASE_URL = get_database_url()

CONNECT_ARGS = {"statement_cache_size": 0}
if DB_SSL_REQUIRE:
    CONNECT_ARGS["ssl"] = True


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool, connect_args=CONNECT_ARGS)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())