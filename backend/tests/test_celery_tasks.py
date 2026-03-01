"""Tests for the Celery agent task — real engine wiring.

Tests verify the _execute_run pipeline: loading task/platforms, setting
status transitions, streaming agent events into StepLogs, and handling
errors. Heavy external deps (Playwright, LangGraph, LangChain) are mocked
via _import_engine patching.
"""

import sys
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock external deps not installed locally
# ---------------------------------------------------------------------------
for mod in (
    "playwright",
    "playwright.async_api",
    "langchain_core",
    "langchain_core.messages",
    "langchain_core.tools",
    "langchain_openai",
    "langgraph",
    "langgraph.graph",
    "langgraph.graph.state",
    "langgraph.graph.message",
    "langgraph.prebuilt",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Fake @tool decorator
_tool_mod = sys.modules["langchain_core.tools"]


def _fake_tool(name_or_func=None, *args, **kwargs):
    def decorator(fn):
        fn.name = name if name else fn.__name__
        fn.description = fn.__doc__ or ""
        return fn
    if callable(name_or_func):
        name = None
        return decorator(name_or_func)
    name = name_or_func
    return decorator


_tool_mod.tool = _fake_tool

from app.models.agent_run import AgentRun, RunStatus
from app.models.agent_task import AgentTask
from app.models.platform import Platform
from app.models.step_log import StepLog


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

    task = AgentTask(name="Test Task", goal="Check employee active time")
    task.platforms = [platform]
    db_session.add(task)
    await db_session.commit()

    run = AgentRun(task_id=task.id, status=RunStatus.PENDING)
    db_session.add(run)
    await db_session.commit()
    return run


class FakeHumanMessage:
    """Minimal stand-in for langchain_core.messages.HumanMessage."""
    def __init__(self, content):
        self.content = content


def _mock_agent_stream(final_content="Active time is 92%, above threshold."):
    """Create an async generator that simulates LangGraph agent streaming."""
    agent_msg_1 = SimpleNamespace(
        content="Let me check the employee data.",
        tool_calls=[{"name": "navigate", "args": {"url": "http://portal/employees"}}],
    )
    tool_msg = SimpleNamespace(
        content="Navigated to http://portal/employees",
        name="navigate",
    )
    agent_msg_final = SimpleNamespace(
        content=final_content,
        tool_calls=[],
    )

    async def stream(initial_state, stream_mode="updates"):
        yield {"agent": {"messages": [agent_msg_1]}}
        yield {"tools": {"messages": [tool_msg]}}
        yield {"agent": {"messages": [agent_msg_final]}}

    return stream


def _mock_browser_pool():
    """Create a mock BrowserPool context manager yielding mock page."""
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()

    mock_pool = AsyncMock()
    mock_pool.new_context = AsyncMock(return_value=mock_context)
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock(return_value=False)

    return mock_pool, mock_page


def _make_import_engine(mock_pool, mock_agent):
    """Create a fake _import_engine that returns mocked components."""
    BrowserPoolCls = MagicMock(return_value=mock_pool)
    generate_tools = MagicMock(return_value=[MagicMock(name="fake_tool")])
    build_system_prompt = MagicMock(return_value="test system prompt")
    build_agent = MagicMock(return_value=mock_agent)

    def fake_import():
        return BrowserPoolCls, generate_tools, build_system_prompt, build_agent, FakeHumanMessage

    return fake_import


# ---------------------------------------------------------------------------
# Full pipeline test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_run_full_pipeline(db_session):
    """Full pipeline: loads task, streams agent, saves StepLogs, publishes to Redis, marks COMPLETED."""
    from app.services.celery_tasks import _execute_run

    run = await _seed_run(db_session)

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    mock_pool, _ = _mock_browser_pool()
    mock_agent = MagicMock()
    mock_agent.astream = _mock_agent_stream("Employee active time is 95%.")

    mock_publish_step = AsyncMock()
    mock_publish_complete = AsyncMock()

    with (
        patch("app.services.celery_tasks.async_session", mock_session_factory),
        patch("app.services.celery_tasks._import_engine", _make_import_engine(mock_pool, mock_agent)),
        patch("app.services.celery_tasks.publish_step", mock_publish_step),
        patch("app.services.celery_tasks.publish_run_complete", mock_publish_complete),
    ):
        await _execute_run(str(run.id))

    await db_session.refresh(run)
    assert run.status == RunStatus.COMPLETED
    assert run.started_at is not None
    assert run.finished_at is not None
    assert "95%" in run.final_answer

    # Verify StepLogs were created
    from sqlalchemy import select
    stmt = select(StepLog).where(StepLog.run_id == run.id).order_by(StepLog.step_index)
    result = await db_session.execute(stmt)
    steps = result.scalars().all()

    assert len(steps) == 3
    assert steps[0].step_type == "agent_thinking"
    assert steps[1].step_type == "tool_call"
    assert steps[1].tool_name == "navigate"
    assert steps[2].step_type == "agent_thinking"

    # Verify Redis publishing
    assert mock_publish_step.call_count == 3
    mock_publish_complete.assert_called_once()
    complete_args = mock_publish_complete.call_args
    assert complete_args[0][1] == "completed"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

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
    """If an exception occurs mid-run, status is set to FAILED and run_complete published."""
    from app.services.celery_tasks import _execute_run

    run = await _seed_run(db_session)

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(side_effect=RuntimeError("Browser launch failed"))
    mock_pool.__aexit__ = AsyncMock(return_value=False)

    def failing_import():
        BrowserPoolCls = MagicMock(return_value=mock_pool)
        return BrowserPoolCls, None, None, None, None

    mock_publish_step = AsyncMock()
    mock_publish_complete = AsyncMock()

    with (
        patch("app.services.celery_tasks.async_session", mock_session_factory),
        patch("app.services.celery_tasks._import_engine", failing_import),
        patch("app.services.celery_tasks.publish_step", mock_publish_step),
        patch("app.services.celery_tasks.publish_run_complete", mock_publish_complete),
    ):
        await _execute_run(str(run.id))

    await db_session.refresh(run)
    assert run.status == RunStatus.FAILED
    assert "Browser launch failed" in run.error
    assert run.finished_at is not None

    # Verify Redis failure event published
    mock_publish_step.assert_not_called()
    mock_publish_complete.assert_called_once()
    complete_args = mock_publish_complete.call_args
    assert complete_args[0][1] == "failed"
    assert "Browser launch failed" in complete_args[1]["error"]


# ---------------------------------------------------------------------------
# Redis pub/sub integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_step_data_matches_step_log(db_session):
    """Published step data includes all StepLog fields for WS clients."""
    from app.services.celery_tasks import _execute_run

    run = await _seed_run(db_session)

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    mock_pool, _ = _mock_browser_pool()
    mock_agent = MagicMock()
    mock_agent.astream = _mock_agent_stream("Done.")

    mock_publish_step = AsyncMock()
    mock_publish_complete = AsyncMock()

    with (
        patch("app.services.celery_tasks.async_session", mock_session_factory),
        patch("app.services.celery_tasks._import_engine", _make_import_engine(mock_pool, mock_agent)),
        patch("app.services.celery_tasks.publish_step", mock_publish_step),
        patch("app.services.celery_tasks.publish_run_complete", mock_publish_complete),
    ):
        await _execute_run(str(run.id))

    # Check the first published step (agent thinking with tool call)
    first_call = mock_publish_step.call_args_list[0]
    assert first_call[0][0] == str(run.id)  # run_id
    step_data = first_call[0][1]
    assert step_data["step_index"] == 0
    assert step_data["step_type"] == "agent_thinking"
    assert step_data["tool_name"] == "navigate"
    assert "agent_reasoning" in step_data
    assert "duration_ms" in step_data

    # Check the second published step (tool result)
    second_call = mock_publish_step.call_args_list[1]
    step_data2 = second_call[0][1]
    assert step_data2["step_index"] == 1
    assert step_data2["step_type"] == "tool_call"
    assert step_data2["tool_name"] == "navigate"
    assert step_data2["tool_output"] is not None


@pytest.mark.asyncio
async def test_publish_run_complete_includes_final_answer(db_session):
    """publish_run_complete is called with the final answer on success."""
    from app.services.celery_tasks import _execute_run

    run = await _seed_run(db_session)

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    mock_pool, _ = _mock_browser_pool()
    mock_agent = MagicMock()
    mock_agent.astream = _mock_agent_stream("Employee active time is 88%.")

    mock_publish_step = AsyncMock()
    mock_publish_complete = AsyncMock()

    with (
        patch("app.services.celery_tasks.async_session", mock_session_factory),
        patch("app.services.celery_tasks._import_engine", _make_import_engine(mock_pool, mock_agent)),
        patch("app.services.celery_tasks.publish_step", mock_publish_step),
        patch("app.services.celery_tasks.publish_run_complete", mock_publish_complete),
    ):
        await _execute_run(str(run.id))

    mock_publish_complete.assert_called_once()
    args, kwargs = mock_publish_complete.call_args
    assert args[0] == str(run.id)
    assert args[1] == "completed"
    assert "88%" in kwargs.get("final_answer", args[2] if len(args) > 2 else "")


# ---------------------------------------------------------------------------
# _create_step_log unit tests
# ---------------------------------------------------------------------------

def test_create_step_log_agent_thinking():
    """_create_step_log correctly parses agent thinking messages."""
    from app.services.celery_tasks import _create_step_log

    msg = SimpleNamespace(content="I need to check the employee data.", tool_calls=[])
    step = _create_step_log(run_id=uuid.uuid4(), step_index=0, node_name="agent", message=msg)
    assert step.step_type == "agent_thinking"
    assert step.agent_reasoning == "I need to check the employee data."
    assert step.tool_name is None


def test_create_step_log_tool_call():
    """_create_step_log correctly parses tool result messages."""
    from app.services.celery_tasks import _create_step_log

    msg = SimpleNamespace(content="Navigated to http://portal/employees", name="navigate")
    step = _create_step_log(run_id=uuid.uuid4(), step_index=1, node_name="tools", message=msg)
    assert step.step_type == "tool_call"
    assert step.tool_name == "navigate"
    assert step.tool_output == {"result": "Navigated to http://portal/employees"}


def test_create_step_log_agent_with_tool_calls():
    """_create_step_log captures tool call info from agent reasoning."""
    from app.services.celery_tasks import _create_step_log

    msg = SimpleNamespace(
        content="Let me navigate to the employees page.",
        tool_calls=[{"name": "navigate", "args": {"url": "http://portal"}}],
    )
    step = _create_step_log(run_id=uuid.uuid4(), step_index=0, node_name="agent", message=msg)
    assert step.step_type == "agent_thinking"
    assert step.tool_name == "navigate"
    assert step.tool_input == {"url": "http://portal"}
    assert step.agent_reasoning == "Let me navigate to the employees page."


def test_create_step_log_screenshot_detection():
    """_create_step_log detects screenshot paths in tool output."""
    from app.services.celery_tasks import _create_step_log

    msg = SimpleNamespace(
        content="Screenshot saved to /tmp/screenshots/dashboard_1234.png",
        name="take_screenshot",
    )
    step = _create_step_log(run_id=uuid.uuid4(), step_index=2, node_name="tools", message=msg)
    assert step.step_type == "tool_call"
    assert step.screenshot_path is not None
    assert "/tmp/screenshots" in step.screenshot_path
