"""MySQL database connection and session management."""

import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy import text as sqlalchemy_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Load .env from backend/ directory
load_dotenv(Path(__file__).parent.parent / ".env")

logger = structlog.get_logger("db")


def _build_database_url() -> str:
    """Build DATABASE_URL from env. Supports full URL or split fields."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Build from individual fields
    user = os.getenv("DB_USER", "fambank")
    password = os.getenv("DB_PASSWORD", "fambank")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "fambank")
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = _build_database_url()

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=2,
    pool_recycle=3600,
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# SQL execution logging via SQLAlchemy events on the sync engine
_sync_engine = engine.sync_engine


@event.listens_for(_sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info["query_start_time"] = time.perf_counter()


@event.listens_for(_sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    start = conn.info.pop("query_start_time", None)
    duration_ms = round((time.perf_counter() - start) * 1000, 2) if start else 0
    logger.debug(
        "sql_executed",
        statement=statement[:500],
        duration_ms=duration_ms,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_transaction_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for explicit transaction control.

    Usage:
        async with get_transaction_session() as session:
            # all operations here are in a single transaction
            ...
        # auto-commits on exit, rolls back on exception
    """
    async with async_session_factory() as session:
        async with session.begin():
            yield session


async def init_db() -> None:
    """Run init.sql and triggers.sql to create tables and triggers."""
    import pathlib

    migrations_dir = pathlib.Path(__file__).parent / "migrations"

    async with engine.begin() as conn:
        # Create tables
        init_sql = (migrations_dir / "init.sql").read_text(encoding="utf-8")
        for statement in _split_sql(init_sql):
            await conn.execute(sqlalchemy_text(statement))

        # Create triggers
        triggers_sql = (migrations_dir / "triggers.sql").read_text(encoding="utf-8")
        for statement in _split_sql_triggers(triggers_sql):
            await conn.execute(sqlalchemy_text(statement))

        # Seed default data
        seed_sql = (migrations_dir / "seed.sql").read_text(encoding="utf-8")
        for statement in _split_sql(seed_sql):
            await conn.execute(sqlalchemy_text(statement))


def _split_sql(sql: str) -> list[str]:
    """Split SQL text into individual statements by semicolon."""
    return [s.strip() for s in sql.split(";") if s.strip()]


def _split_sql_triggers(sql: str) -> list[str]:
    """Split trigger SQL that uses DELIMITER $$ ... $$ syntax."""
    statements = []
    # Handle DELIMITER blocks
    parts = sql.split("DELIMITER")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("$$"):
            # Inside a DELIMITER $$ block
            inner = part[2:]  # remove leading $$
            # Split by $$ to get trigger bodies
            trigger_parts = inner.split("$$")
            for tp in trigger_parts:
                tp = tp.strip()
                if tp and tp != ";":
                    statements.append(tp)
        else:
            # Regular SQL outside DELIMITER blocks
            for s in _split_sql(part):
                if s:
                    statements.append(s)
    return statements

