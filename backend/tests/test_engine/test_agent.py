"""Tests for the LangGraph ReAct agent builder."""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock external deps not installed locally
# ---------------------------------------------------------------------------
for mod in (
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

# Provide realistic mocks for the graph builder API
_mock_langgraph = sys.modules["langgraph.graph"]
_mock_prebuilt = sys.modules["langgraph.prebuilt"]


class _FakeStateGraph:
    """Lightweight stand-in for langgraph.graph.StateGraph."""

    def __init__(self, state_class):
        self.state_class = state_class
        self.nodes = {}
        self.entry = None
        self.edges = []
        self.conditional_edges = []

    def add_node(self, name, fn):
        self.nodes[name] = fn

    def set_entry_point(self, name):
        self.entry = name

    def add_conditional_edges(self, source, condition_fn, mapping):
        self.conditional_edges.append((source, condition_fn, mapping))

    def add_edge(self, source, target):
        self.edges.append((source, target))

    def compile(self):
        return SimpleNamespace(
            nodes=self.nodes,
            entry=self.entry,
            edges=self.edges,
            conditional_edges=self.conditional_edges,
            state_class=self.state_class,
        )


_mock_langgraph.StateGraph = _FakeStateGraph
_mock_langgraph.END = "__end__"

# ToolNode mock — just stores the tools
_mock_prebuilt.ToolNode = lambda tools: SimpleNamespace(tools=tools, name="ToolNode")

# Fake ChatOpenAI
_mock_llm_instance = MagicMock()
_mock_llm_instance.bind_tools = MagicMock(return_value=_mock_llm_instance)
_mock_llm_instance.ainvoke = AsyncMock(
    return_value=SimpleNamespace(content="final answer", tool_calls=[])
)

sys.modules["langchain_openai"].ChatOpenAI = MagicMock(return_value=_mock_llm_instance)

# Fake SystemMessage
sys.modules["langchain_core.messages"].SystemMessage = type(
    "SystemMessage", (), {"__init__": lambda self, content: setattr(self, "content", content)}
)

from app.engine.agent import build_agent, _should_continue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_tool(name="test_tool"):
    t = MagicMock()
    t.name = name
    return t


# ---------------------------------------------------------------------------
# _should_continue tests
# ---------------------------------------------------------------------------

class TestShouldContinue:
    def test_routes_to_tools_when_tool_calls_present(self):
        last_msg = SimpleNamespace(tool_calls=[{"name": "navigate", "args": {}}])
        state = {"messages": [last_msg]}
        assert _should_continue(state) == "tools"

    def test_routes_to_end_when_no_tool_calls(self):
        last_msg = SimpleNamespace(tool_calls=[])
        state = {"messages": [last_msg]}
        assert _should_continue(state) == "__end__"

    def test_routes_to_end_when_tool_calls_attr_missing(self):
        last_msg = SimpleNamespace()  # no tool_calls attribute
        state = {"messages": [last_msg]}
        assert _should_continue(state) == "__end__"


# ---------------------------------------------------------------------------
# build_agent tests
# ---------------------------------------------------------------------------

class TestBuildAgent:
    def test_returns_compiled_graph_with_two_nodes(self):
        tools = [_fake_tool("navigate"), _fake_tool("scrape")]
        with patch("app.engine.agent.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test"
            graph = build_agent(tools, system_prompt="You are an agent.")

        assert "agent" in graph.nodes
        assert "tools" in graph.nodes

    def test_entry_point_is_agent(self):
        tools = [_fake_tool()]
        with patch("app.engine.agent.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test"
            graph = build_agent(tools, system_prompt="test")

        assert graph.entry == "agent"

    def test_tools_edge_routes_back_to_agent(self):
        tools = [_fake_tool()]
        with patch("app.engine.agent.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test"
            graph = build_agent(tools, system_prompt="test")

        assert ("tools", "agent") in graph.edges

    def test_conditional_edge_from_agent(self):
        tools = [_fake_tool()]
        with patch("app.engine.agent.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test"
            graph = build_agent(tools, system_prompt="test")

        # Should have exactly one conditional edge from "agent"
        assert len(graph.conditional_edges) == 1
        source, condition_fn, mapping = graph.conditional_edges[0]
        assert source == "agent"
        assert "tools" in mapping
        assert "__end__" in mapping.values()

    def test_binds_tools_to_llm(self):
        tools = [_fake_tool("t1"), _fake_tool("t2")]
        with patch("app.engine.agent.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test"
            build_agent(tools, system_prompt="test")

        _mock_llm_instance.bind_tools.assert_called_with(tools)

    @pytest.mark.asyncio
    async def test_agent_node_prepends_system_prompt(self):
        tools = [_fake_tool()]
        with patch("app.engine.agent.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test"
            graph = build_agent(tools, system_prompt="You are an AI agent.")

        agent_fn = graph.nodes["agent"]
        state = {"messages": [SimpleNamespace(content="hello")]}
        result = await agent_fn(state)

        # ainvoke should have been called with system prompt prepended
        call_args = _mock_llm_instance.ainvoke.call_args[0][0]
        assert call_args[0].content == "You are an AI agent."
        assert "messages" in result
