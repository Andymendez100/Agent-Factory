import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from app.models.agent_run import AgentRun, RunStatus
from app.models.agent_task import AgentTask
from app.models.platform import Platform


FAKE_PLATFORM_KWARGS = dict(
    name="Test Portal",
    base_url="https://portal.example.com",
    login_url="https://portal.example.com/login",
    credentials_encrypted=b"fake-encrypted-data",
    login_selectors={"username_field": "#email"},
)


async def _seed_run(db_session) -> AgentRun:
    """Create a platform → task → pending run and return the run."""
    platform = Platform(**FAKE_PLATFORM_KWARGS)
    db_session.add(platform)
    await db_session.commit()

    task = AgentTask(name="Test Task", goal="Do something")
    task.platforms = [platform]
    db_session.add(task)
    await db_session.commit()

    run = AgentRun(task_id=task.id, status=RunStatus.PENDING)
    db_session.add(run)
    await db_session.commit()
    return run


@pytest.mark.asyncio
async def test_execute_run_completes(db_session):
    """Placeholder task transitions PENDING → RUNNING → COMPLETED."""
    from app.services.celery_tasks import _execute_run

    run = await _seed_run(db_session)

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    with patch("app.services.celery_tasks.async_session", mock_session_factory), \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await _execute_run(str(run.id))

    mock_sleep.assert_awaited_once_with(5)

    await db_session.refresh(run)
    assert run.status == RunStatus.COMPLETED
    assert run.started_at is not None
    assert run.finished_at is not None
    assert run.final_answer == "Placeholder: agent task completed successfully."


@pytest.mark.asyncio
async def test_execute_run_not_found(db_session):
    """Gracefully handles a missing run_id without raising."""
    from app.services.celery_tasks import _execute_run

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    fake_id = str(uuid.uuid4())
    with patch("app.services.celery_tasks.async_session", mock_session_factory):
        await _execute_run(fake_id)  # should not raise


@pytest.mark.asyncio
async def test_execute_run_marks_failed_on_error(db_session):
    """If an exception occurs mid-run, status is set to FAILED."""
    from app.services.celery_tasks import _execute_run

    run = await _seed_run(db_session)

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    async def boom(seconds):
        raise RuntimeError("simulated failure")

    with patch("app.services.celery_tasks.async_session", mock_session_factory), \
         patch("asyncio.sleep", side_effect=boom):
        await _execute_run(str(run.id))

    await db_session.refresh(run)
    assert run.status == RunStatus.FAILED
    assert "simulated failure" in run.error
    assert run.finished_at is not None
