"""Tests for the database seed script (demo platform + sample task).

Verifies:
- seed_demo_data creates Platform and AgentTask records
- Idempotent: running twice doesn't create duplicates
- Platform has correct selectors and encrypted credentials
- Task is linked to the platform via M2M
"""

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.agent_task import AgentTask
from app.models.platform import Platform

# Use the same TEST_KEY approach as conftest
TEST_KEY = Fernet.generate_key().decode()


@pytest.mark.asyncio
async def test_seed_creates_platform_and_task(db_session):
    """seed_demo_data creates a Platform and AgentTask on first run."""
    from app.db.seed import seed_demo_data, PLATFORM_NAME, TASK_NAME

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    with (
        patch("app.db.seed.async_session", mock_session_factory),
        patch("app.db.seed.settings") as mock_settings,
        patch("app.services.crypto.settings") as mock_crypto_settings,
    ):
        mock_settings.FERNET_KEY = TEST_KEY
        mock_crypto_settings.FERNET_KEY = TEST_KEY
        await seed_demo_data()

    # Verify platform created
    stmt = select(Platform).where(Platform.name == PLATFORM_NAME)
    result = await db_session.execute(stmt)
    platform = result.scalar_one()
    assert platform.login_url == "http://mock-portal:8001/login"
    assert platform.login_selectors["username_field"] == "#username"
    assert platform.login_selectors["password_field"] == "#password"
    assert platform.login_selectors["submit_button"] == "button[type='submit']"

    # Verify task created
    stmt = select(AgentTask).where(AgentTask.name == TASK_NAME).options(
        selectinload(AgentTask.platforms)
    )
    result = await db_session.execute(stmt)
    task = result.scalar_one()
    assert "Maria Santos" in task.goal
    assert task.constraints["threshold"] == 0.90
    assert len(task.platforms) == 1
    assert task.platforms[0].name == PLATFORM_NAME


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session):
    """Running seed_demo_data twice doesn't create duplicate records."""
    from app.db.seed import seed_demo_data, PLATFORM_NAME, TASK_NAME

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    with (
        patch("app.db.seed.async_session", mock_session_factory),
        patch("app.db.seed.settings") as mock_settings,
        patch("app.services.crypto.settings") as mock_crypto_settings,
    ):
        mock_settings.FERNET_KEY = TEST_KEY
        mock_crypto_settings.FERNET_KEY = TEST_KEY
        await seed_demo_data()
        await seed_demo_data()  # Second call should be a no-op

    # Still only one platform and one task
    result = await db_session.execute(select(Platform))
    platforms = result.scalars().all()
    assert len(platforms) == 1

    result = await db_session.execute(select(AgentTask))
    tasks = result.scalars().all()
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_seed_credentials_are_encrypted(db_session):
    """Seeded platform credentials are Fernet-encrypted, not plaintext."""
    from app.db.seed import seed_demo_data, PLATFORM_NAME

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    with (
        patch("app.db.seed.async_session", mock_session_factory),
        patch("app.db.seed.settings") as mock_settings,
        patch("app.services.crypto.settings") as mock_crypto_settings,
    ):
        mock_settings.FERNET_KEY = TEST_KEY
        mock_crypto_settings.FERNET_KEY = TEST_KEY
        await seed_demo_data()

    stmt = select(Platform).where(Platform.name == PLATFORM_NAME)
    result = await db_session.execute(stmt)
    platform = result.scalar_one()

    # Credentials should be encrypted bytes, not plaintext JSON
    assert isinstance(platform.credentials_encrypted, bytes)
    assert b"admin" not in platform.credentials_encrypted
    assert b"demo123" not in platform.credentials_encrypted

    # But should be decryptable with the right key
    fernet = Fernet(TEST_KEY.encode())
    import json
    decrypted = json.loads(fernet.decrypt(platform.credentials_encrypted))
    assert decrypted["username"] == "admin"
    assert decrypted["password"] == "demo123"
