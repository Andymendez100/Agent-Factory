import asyncio
import json as json_mod
import sqlite3
import uuid

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, String, TypeDecorator, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import patch

from app.models.base import Base
from app.db.session import get_db
from app.main import app

TEST_KEY = Fernet.generate_key().decode()

# Register UUID adapter for SQLite
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))


class StringUUID(TypeDecorator):
    """SQLite-compatible UUID type: stores as String(36), accepts UUID objects."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value) if not isinstance(value, uuid.UUID) else value
        return value


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _patch_pg_types_for_sqlite():
    """Replace PG-specific column types with SQLite-compatible equivalents."""
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()
            elif isinstance(col.type, UUID):
                col.type = StringUUID()


@pytest_asyncio.fixture
async def db_session():
    """In-memory SQLite async engine for tests."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _patch_pg_types_for_sqlite()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """FastAPI test client with DB and FERNET_KEY overrides."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    fernet = Fernet(TEST_KEY.encode())

    with patch("app.services.crypto.settings") as mock_settings, \
         patch("app.api.platforms.encrypt_credentials") as mock_encrypt:
        mock_settings.FERNET_KEY = TEST_KEY
        mock_encrypt.side_effect = lambda data: fernet.encrypt(
            json_mod.dumps(data).encode()
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()
