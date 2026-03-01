"""Tests for AgentState and build_system_prompt."""

import json
import sys
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import MagicMock

# Mock langchain/langgraph modules that may not be installed locally
for mod in (
    "langchain_core",
    "langchain_core.messages",
    "langgraph",
    "langgraph.graph",
    "langgraph.graph.message",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from app.engine.state import AgentState
from app.engine.prompts import build_system_prompt


# ---------------------------------------------------------------------------
# Helpers: lightweight stand-ins for ORM models (avoid DB dependency)
# ---------------------------------------------------------------------------

def _make_platform(name: str = "Sprout Portal") -> SimpleNamespace:
    return SimpleNamespace(name=name)


def _make_task(
    goal: str = "Check active time for employee #1234",
    constraints: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(goal=goal, constraints=constraints)


# ---------------------------------------------------------------------------
# AgentState tests
# ---------------------------------------------------------------------------

class TestAgentState:
    def test_state_has_required_keys(self):
        hints = get_type_hints(AgentState, include_extras=True)
        assert "messages" in hints
        assert "run_id" in hints
        assert "platform_configs" in hints

    def test_state_can_be_instantiated(self):
        state: AgentState = {
            "messages": [{"role": "user", "content": "hello"}],
            "run_id": "abc-123",
            "platform_configs": [{"name": "portal"}],
        }
        assert state["run_id"] == "abc-123"
        assert len(state["messages"]) == 1

    def test_messages_accept_list(self):
        state: AgentState = {
            "messages": [
                {"role": "user", "content": "What is the active time?"},
                {"role": "assistant", "content": "Let me check."},
            ],
            "run_id": "run-1",
            "platform_configs": [],
        }
        assert len(state["messages"]) == 2


# ---------------------------------------------------------------------------
# build_system_prompt tests
# ---------------------------------------------------------------------------

class TestBuildSystemPrompt:
    def test_basic_prompt_contains_goal(self):
        task = _make_task(goal="Check KPI dashboard")
        prompt = build_system_prompt(task, [])
        assert "Check KPI dashboard" in prompt

    def test_prompt_lists_platform_names(self):
        task = _make_task()
        platforms = [_make_platform("Sprout"), _make_platform("Five9")]
        prompt = build_system_prompt(task, platforms)
        assert "Sprout, Five9" in prompt

    def test_prompt_shows_none_when_no_platforms(self):
        task = _make_task()
        prompt = build_system_prompt(task, [])
        assert "Available platforms: none" in prompt

    def test_prompt_includes_constraints_when_present(self):
        constraints = {"threshold": 0.90, "metric": "active_time_pct"}
        task = _make_task(constraints=constraints)
        prompt = build_system_prompt(task, [])
        assert "Constraints:" in prompt
        assert "threshold" in prompt
        assert "0.9" in prompt

    def test_prompt_omits_constraints_when_none(self):
        task = _make_task(constraints=None)
        prompt = build_system_prompt(task, [])
        assert "Constraints:" not in prompt

    def test_prompt_includes_instructions(self):
        task = _make_task()
        prompt = build_system_prompt(task, [])
        assert "Instructions:" in prompt
        assert "login tools" in prompt
        assert "screenshots" in prompt
