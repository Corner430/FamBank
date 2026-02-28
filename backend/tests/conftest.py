"""Test fixtures: test DB setup/teardown, seeded accounts, shared helpers."""

import os
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use test database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "mysql+aiomysql://fambank:fambank@localhost:3306/fambank_test",
)

# Module-level flag to track if DB schema is initialized
_schema_initialized = False


@pytest_asyncio.fixture
async def db_session():
    """Provide a database session for each test with clean data."""
    global _schema_initialized

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    try:
        if not _schema_initialized:
            # First test: set up schema
            await _setup_schema(engine)
            _schema_initialized = True

        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with session_factory() as session:
            # Clean all data before each test
            await _clean_tables(session)
            yield session

    finally:
        await engine.dispose()


async def _setup_schema(engine):
    """Create tables and triggers (idempotent)."""
    import pathlib

    migrations_dir = pathlib.Path(__file__).parent.parent / "app" / "migrations"

    async with engine.begin() as conn:
        # Drop all existing tables for clean state
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        result = await conn.execute(text("SHOW TABLES"))
        tables = result.fetchall()
        for (table_name,) in tables:
            if table_name == "transaction_log":
                await conn.execute(text("DROP TRIGGER IF EXISTS trg_transaction_log_no_update"))
                await conn.execute(text("DROP TRIGGER IF EXISTS trg_transaction_log_no_delete"))
            await conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

        # Create tables
        init_sql = (migrations_dir / "init.sql").read_text(encoding="utf-8")
        for statement in _split_sql(init_sql):
            await conn.execute(text(statement))

        # Create triggers
        triggers_sql = (migrations_dir / "triggers.sql").read_text(encoding="utf-8")
        for statement in _split_sql_triggers(triggers_sql):
            await conn.execute(text(statement))


async def _clean_tables(session: AsyncSession):
    """Truncate all tables and recreate triggers for a clean test."""
    await session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    tables = [
        "escrow", "debt", "announcement", "config",
        "violation", "wish_item", "wish_list",
        "transaction_log", "settlement", "account", "user",
    ]
    # Drop triggers so we can truncate transaction_log
    await session.execute(text("DROP TRIGGER IF EXISTS trg_transaction_log_no_update"))
    await session.execute(text("DROP TRIGGER IF EXISTS trg_transaction_log_no_delete"))
    await session.commit()

    for table in tables:
        await session.execute(text(f"TRUNCATE TABLE `{table}`"))
    await session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    await session.commit()

    # Re-create triggers
    await session.execute(text("""
        CREATE TRIGGER trg_transaction_log_no_update
        BEFORE UPDATE ON transaction_log
        FOR EACH ROW
        BEGIN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'AUDIT VIOLATION: transaction_log records cannot be updated';
        END
    """))
    await session.execute(text("""
        CREATE TRIGGER trg_transaction_log_no_delete
        BEFORE DELETE ON transaction_log
        FOR EACH ROW
        BEGIN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'AUDIT VIOLATION: transaction_log records cannot be deleted';
        END
    """))
    await session.commit()


@pytest_asyncio.fixture
async def seeded_accounts(db_session: AsyncSession):
    """Seed the 3 accounts (A/B/C) with zero balance."""
    await db_session.execute(text("""
        INSERT INTO account (account_type, display_name, balance, interest_pool)
        VALUES ('A', '零钱宝', 0, 0), ('B', '梦想金', 0, 0), ('C', '牛马金', 0, 0)
    """))
    await db_session.commit()
    return db_session


@pytest_asyncio.fixture
async def seeded_config(db_session: AsyncSession):
    """Seed default config values."""
    import pathlib

    seed_sql = (
        pathlib.Path(__file__).parent.parent / "app" / "migrations" / "seed.sql"
    ).read_text(encoding="utf-8")
    for statement in _split_sql(seed_sql):
        await db_session.execute(text(statement))
    await db_session.commit()
    return db_session


@pytest_asyncio.fixture
async def seeded_all(seeded_accounts, seeded_config):
    """Seed accounts + config."""
    return seeded_accounts


@pytest_asyncio.fixture
async def async_client(seeded_all):
    """Provide an async HTTP client wired to the FastAPI app with test DB."""
    from app.database import get_db
    from app.main import app

    async def override_get_db():
        yield seeded_all

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# --- Helpers ---

def assert_cents(actual: int, expected_yuan: str, msg: str = ""):
    """Assert integer cents equals expected yuan string."""
    expected_cents = int(Decimal(expected_yuan) * 100)
    assert actual == expected_cents, f"{msg}: expected {expected_yuan} ({expected_cents}¢), got {actual}¢"


def _split_sql(sql: str) -> list[str]:
    return [s.strip() for s in sql.split(";") if s.strip()]


def _split_sql_triggers(sql: str) -> list[str]:
    statements = []
    parts = sql.split("DELIMITER")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("$$"):
            inner = part[2:]
            trigger_parts = inner.split("$$")
            for tp in trigger_parts:
                tp = tp.strip()
                if tp and tp != ";":
                    statements.append(tp)
        else:
            for s in _split_sql(part):
                if s:
                    statements.append(s)
    return statements
