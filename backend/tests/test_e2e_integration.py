"""End-to-end integration test: API → Celery → Agent → Mock Portal → Result.

This test exercises the full application flow using the FastAPI test client
and mocked engine components (Playwright, LangGraph, LangChain, Redis).
It creates resources via the API layer, simulates agent execution through
the Celery task pipeline, then verifies results via the API layer.

The mock agent stream simulates a realistic BPO scenario:
  1. Agent reasons about logging into the portal
  2. Calls login tool with credentials
  3. Navigates to employee directory
  4. Scrapes the employee table
  5. Takes a screenshot
  6. Analyzes the data and produces a final answer
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


# ---------------------------------------------------------------------------
# Realistic mock agent stream — simulates a full BPO task execution
# ---------------------------------------------------------------------------

EMPLOYEE_DATA = {
    "headers": ["Employee", "Emp ID", "Dept", "Active Time %"],
    "rows": [
        ["Maria Santos", "EMP-0001", "Customer Service", "92.3%"],
        ["Jose Rivera", "EMP-0002", "Customer Service", "95.1%"],
        ["Ana Reyes", "EMP-0003", "Technical Support", "87.4%"],
    ],
}

FINAL_ANALYSIS = (
    "Employee Performance Report — Maria Santos (EMP-0001)\n"
    "Department: Customer Service\n"
    "Average Active Time: 92.3%\n\n"
    "Maria Santos' active time of 92.3% is above the 90% threshold. "
    "However, on 2 of the last 14 days, her active time dipped below 90%:\n"
    "- Feb 14: 88.5%\n"
    "- Feb 21: 89.1%\n\n"
    "Overall performance is satisfactory but shows occasional dips. "
    "Recommend monitoring for consistent improvement."
)


def _realistic_agent_stream():
    """Simulates a full ReAct agent loop for a BPO check-employee task.

    Yields 8 events total (4 agent thinking + 4 tool results):
    1. Agent reasons → login tool call
    2. Login tool result → success
    3. Agent reasons → navigate to employees
    4. Navigate tool result → page loaded
    5. Agent reasons → scrape table
    6. Scrape tool result → employee data JSON
    7. Agent reasons → screenshot
    8. Screenshot tool result → saved
    9. Agent final answer
    """
    events = [
        # Step 0: Agent decides to login
        {"agent": {"messages": [SimpleNamespace(
            content="I need to log into the BPO Employee Portal first. Let me use the login tool.",
            tool_calls=[{
                "name": "login_bpo_employee_portal",
                "args": {"username": "admin", "password": "demo123"},
            }],
        )]}},
        # Step 1: Login succeeds
        {"tools": {"messages": [SimpleNamespace(
            content="Successfully logged in as admin",
            name="login_bpo_employee_portal",
        )]}},
        # Step 2: Agent navigates
        {"agent": {"messages": [SimpleNamespace(
            content="Good, I'm logged in. Now I need to navigate to the employee directory to find Maria Santos.",
            tool_calls=[{
                "name": "navigate",
                "args": {"url": "http://mock-portal:8001/employees"},
            }],
        )]}},
        # Step 3: Navigation result
        {"tools": {"messages": [SimpleNamespace(
            content="Navigated to http://mock-portal:8001/employees",
            name="navigate",
        )]}},
        # Step 4: Agent scrapes table
        {"agent": {"messages": [SimpleNamespace(
            content="I can see the employees page. Let me scrape the table data to find Maria Santos.",
            tool_calls=[{
                "name": "scrape_table",
                "args": {"selector": "table.employees"},
            }],
        )]}},
        # Step 5: Scrape result with employee data
        {"tools": {"messages": [SimpleNamespace(
            content=str(EMPLOYEE_DATA),
            name="scrape_table",
        )]}},
        # Step 6: Agent takes screenshot
        {"agent": {"messages": [SimpleNamespace(
            content="Let me take a screenshot for the record before analyzing.",
            tool_calls=[{
                "name": "take_screenshot",
                "args": {},
            }],
        )]}},
        # Step 7: Screenshot result
        {"tools": {"messages": [SimpleNamespace(
            content="Screenshot saved to /tmp/screenshots/employees_1709164800.png",
            name="take_screenshot",
        )]}},
        # Step 8: Final answer (no tool calls)
        {"agent": {"messages": [SimpleNamespace(
            content=FINAL_ANALYSIS,
            tool_calls=[],
        )]}},
    ]

    async def stream(initial_state, stream_mode="updates"):
        for event in events:
            yield event

    return stream


class FakeHumanMessage:
    """Minimal stand-in for langchain_core.messages.HumanMessage."""
    def __init__(self, content):
        self.content = content


def _mock_browser_pool():
    """Create a mock BrowserPool context manager."""
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
    build_system_prompt = MagicMock(return_value="You are a BPO agent...")
    build_agent = MagicMock(return_value=mock_agent)

    def fake_import():
        return BrowserPoolCls, generate_tools, build_system_prompt, build_agent, FakeHumanMessage

    return fake_import


# ---------------------------------------------------------------------------
# End-to-end integration test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_full_flow(client, db_session):
    """Full end-to-end: create platform → create task → trigger run →
    execute agent → verify run completed with analysis result.

    This test drives the entire application through the API layer,
    then simulates agent execution via _execute_run (mocked Celery),
    and verifies the results via the API layer again.
    """
    # ── Step 1: Create a platform via API ─────────────────────
    platform_resp = await client.post("/api/platforms", json={
        "name": "BPO Employee Portal",
        "base_url": "http://mock-portal:8001",
        "login_url": "http://mock-portal:8001/login",
        "credentials": {"username": "admin", "password": "demo123"},
        "login_selectors": {
            "username_field": "#username",
            "password_field": "#password",
            "submit_button": "button[type='submit']",
        },
    })
    assert platform_resp.status_code == 201, platform_resp.text
    platform = platform_resp.json()
    platform_id = platform["id"]
    assert platform["name"] == "BPO Employee Portal"
    assert platform["login_selectors"]["username_field"] == "#username"

    # ── Step 2: Create a task linked to the platform ──────────
    task_resp = await client.post("/api/tasks", json={
        "name": "Check Active Time — Maria Santos",
        "goal": (
            "Log into the BPO Employee Portal, navigate to the employee "
            "directory, find Maria Santos (EMP-0001), and check her active "
            "time percentage. Flag any days below 90%."
        ),
        "platform_ids": [platform_id],
        "constraints": {
            "threshold": 0.90,
            "metric": "active_time_pct",
            "employee_name": "Maria Santos",
        },
    })
    assert task_resp.status_code == 201, task_resp.text
    task = task_resp.json()
    task_id = task["id"]
    assert task["name"] == "Check Active Time — Maria Santos"
    assert len(task["platforms"]) == 1
    assert task["platforms"][0]["name"] == "BPO Employee Portal"

    # ── Step 3: Trigger a run via API ─────────────────────────
    run_resp = await client.post(f"/api/tasks/{task_id}/run")
    assert run_resp.status_code == 201, run_resp.text
    run = run_resp.json()
    run_id = run["id"]
    assert run["status"] == "pending"
    assert run["task_id"] == task_id
    assert run["steps"] == []

    # ── Step 4: Execute the agent (simulated Celery task) ─────
    from app.services.celery_tasks import _execute_run

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    mock_pool, _ = _mock_browser_pool()
    mock_agent = MagicMock()
    mock_agent.astream = _realistic_agent_stream()

    mock_publish_step = AsyncMock()
    mock_publish_complete = AsyncMock()

    with (
        patch("app.services.celery_tasks.async_session", mock_session_factory),
        patch("app.services.celery_tasks._import_engine",
              _make_import_engine(mock_pool, mock_agent)),
        patch("app.services.celery_tasks.publish_step", mock_publish_step),
        patch("app.services.celery_tasks.publish_run_complete",
              mock_publish_complete),
    ):
        await _execute_run(run_id)

    # ── Step 5: Verify run completed via API ──────────────────
    status_resp = await client.get(f"/api/runs/{run_id}")
    assert status_resp.status_code == 200
    completed_run = status_resp.json()

    assert completed_run["status"] == "completed"
    assert completed_run["started_at"] is not None
    assert completed_run["finished_at"] is not None
    assert "Maria Santos" in completed_run["final_answer"]
    assert "92.3%" in completed_run["final_answer"]
    assert "satisfactory" in completed_run["final_answer"].lower()

    # ── Step 6: Verify step logs via API ──────────────────────
    steps = completed_run["steps"]
    assert len(steps) == 9  # 5 agent thinking + 4 tool results

    # First step: agent decides to login
    assert steps[0]["step_type"] == "agent_thinking"
    assert steps[0]["tool_name"] == "login_bpo_employee_portal"
    assert "log into" in steps[0]["agent_reasoning"].lower()

    # Second step: login tool result
    assert steps[1]["step_type"] == "tool_call"
    assert steps[1]["tool_name"] == "login_bpo_employee_portal"
    assert "logged in" in steps[1]["tool_output"]["result"].lower()

    # Navigation steps
    assert steps[2]["step_type"] == "agent_thinking"
    assert steps[2]["tool_name"] == "navigate"
    assert steps[3]["step_type"] == "tool_call"
    assert steps[3]["tool_name"] == "navigate"

    # Scrape steps
    assert steps[4]["step_type"] == "agent_thinking"
    assert steps[4]["tool_name"] == "scrape_table"
    assert steps[5]["step_type"] == "tool_call"
    assert steps[5]["tool_name"] == "scrape_table"

    # Screenshot steps — verify screenshot detection
    assert steps[6]["step_type"] == "agent_thinking"
    assert steps[6]["tool_name"] == "take_screenshot"
    assert steps[7]["step_type"] == "tool_call"
    assert steps[7]["tool_name"] == "take_screenshot"
    assert steps[7]["screenshot_path"] is not None
    assert "/tmp/screenshots" in steps[7]["screenshot_path"]

    # Final answer step
    assert steps[8]["step_type"] == "agent_thinking"
    assert steps[8]["agent_reasoning"] == FINAL_ANALYSIS

    # ── Step 7: Verify Redis pub/sub was called correctly ─────
    # Each of the 9 steps should have been published
    assert mock_publish_step.call_count == 9

    # run_complete should have been called with status=completed
    mock_publish_complete.assert_called_once()
    complete_args, complete_kwargs = mock_publish_complete.call_args
    assert complete_args[0] == run_id
    assert complete_args[1] == "completed"
    final_ans = complete_kwargs.get("final_answer", "")
    assert "Maria Santos" in final_ans


@pytest.mark.asyncio
async def test_e2e_run_failure_flow(client, db_session):
    """End-to-end: trigger run → agent fails → verify FAILED status via API."""
    # Create platform + task via API
    platform_resp = await client.post("/api/platforms", json={
        "name": "Failing Portal",
        "base_url": "http://portal-down:8001",
        "login_url": "http://portal-down:8001/login",
        "credentials": {"username": "test", "password": "test"},
        "login_selectors": {"username_field": "#user"},
    })
    assert platform_resp.status_code == 201
    p_id = platform_resp.json()["id"]

    task_resp = await client.post("/api/tasks", json={
        "name": "Failing Task",
        "goal": "Do something impossible",
        "platform_ids": [p_id],
    })
    assert task_resp.status_code == 201
    t_id = task_resp.json()["id"]

    run_resp = await client.post(f"/api/tasks/{t_id}/run")
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    # Simulate agent failure
    from app.services.celery_tasks import _execute_run

    @asynccontextmanager
    async def mock_session_factory():
        yield db_session

    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(
        side_effect=ConnectionError("Portal unreachable")
    )
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
        patch("app.services.celery_tasks.publish_run_complete",
              mock_publish_complete),
    ):
        await _execute_run(run_id)

    # Verify via API
    status_resp = await client.get(f"/api/runs/{run_id}")
    assert status_resp.status_code == 200
    failed_run = status_resp.json()

    assert failed_run["status"] == "failed"
    assert "Portal unreachable" in failed_run["error"]
    assert failed_run["started_at"] is not None
    assert failed_run["finished_at"] is not None
    assert failed_run["steps"] == []

    # Redis failure published
    mock_publish_step.assert_not_called()
    mock_publish_complete.assert_called_once()
    assert mock_publish_complete.call_args[0][1] == "failed"


@pytest.mark.asyncio
async def test_e2e_cancel_pending_run(client, db_session):
    """End-to-end: trigger run → cancel before execution → verify CANCELLED."""
    # Create platform + task
    platform_resp = await client.post("/api/platforms", json={
        "name": "Cancel Test Portal",
        "base_url": "http://cancel-test:8001",
        "login_url": "http://cancel-test:8001/login",
        "credentials": {"username": "u", "password": "p"},
        "login_selectors": {"username_field": "#u"},
    })
    assert platform_resp.status_code == 201

    task_resp = await client.post("/api/tasks", json={
        "name": "Cancel Test Task",
        "goal": "This will be cancelled",
        "platform_ids": [platform_resp.json()["id"]],
    })
    assert task_resp.status_code == 201

    run_resp = await client.post(f"/api/tasks/{task_resp.json()['id']}/run")
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]
    assert run_resp.json()["status"] == "pending"

    # Cancel the pending run
    cancel_resp = await client.post(f"/api/runs/{run_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Verify via GET
    status_resp = await client.get(f"/api/runs/{run_id}")
    assert status_resp.json()["status"] == "cancelled"

    # Cannot cancel again
    second_cancel = await client.post(f"/api/runs/{run_id}/cancel")
    assert second_cancel.status_code == 409


@pytest.mark.asyncio
async def test_e2e_runs_list(client, db_session):
    """End-to-end: create multiple runs → verify list endpoint returns them."""
    # Create platform + task
    platform_resp = await client.post("/api/platforms", json={
        "name": "List Test Portal",
        "base_url": "http://list-test:8001",
        "login_url": "http://list-test:8001/login",
        "credentials": {"username": "u", "password": "p"},
        "login_selectors": {"username_field": "#u"},
    })
    assert platform_resp.status_code == 201

    task_resp = await client.post("/api/tasks", json={
        "name": "List Test Task",
        "goal": "List test goal",
        "platform_ids": [platform_resp.json()["id"]],
    })
    assert task_resp.status_code == 201
    t_id = task_resp.json()["id"]

    # Create 3 runs
    run_ids = []
    for _ in range(3):
        resp = await client.post(f"/api/tasks/{t_id}/run")
        assert resp.status_code == 201
        run_ids.append(resp.json()["id"])

    # List runs
    list_resp = await client.get("/api/runs")
    assert list_resp.status_code == 200
    runs = list_resp.json()

    # All our runs should be in the list
    listed_ids = {r["id"] for r in runs}
    for rid in run_ids:
        assert rid in listed_ids

    # Verify list is non-empty and has at least our 3 runs
    assert len(runs) >= 3
