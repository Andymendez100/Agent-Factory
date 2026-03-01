"""Tests for the dynamic tool generator."""

import sys
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
    "langchain_core.tools",
    "langchain_openai",
    "langgraph",
    "langgraph.graph",
    "langgraph.graph.message",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Fake @tool decorator (same as test_browser.py)
_real_tool_mod = sys.modules["langchain_core.tools"]


def _fake_tool(name_or_func=None, *args, **kwargs):
    def decorator(fn):
        fn.name = name if name else fn.__name__
        fn.description = fn.__doc__ or ""
        return fn

    if callable(name_or_func):
        name = None
        return decorator(name_or_func)
    else:
        name = name_or_func
        return decorator


_real_tool_mod.tool = _fake_tool

from app.engine.tool_generator import generate_tools


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_page() -> AsyncMock:
    page = AsyncMock()
    page.url = "http://localhost"
    return page


def _mock_platform(name="Test Portal", login_url="http://portal/login"):
    return SimpleNamespace(
        name=name,
        login_url=login_url,
        credentials_encrypted=b"encrypted-bytes",
        login_selectors={
            "username_field": "#user",
            "password_field": "#pass",
            "submit_button": "#login",
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateTools:
    @patch("app.engine.tool_generator.decrypt_credentials")
    def test_returns_correct_count_single_platform(self, mock_decrypt):
        mock_decrypt.return_value = {"username": "admin", "password": "secret"}
        page = _mock_page()
        platforms = [_mock_platform()]

        tools = generate_tools(platforms, page)

        # 1 login + 5 browser + 3 data/action = 9
        assert len(tools) == 9

    @patch("app.engine.tool_generator.decrypt_credentials")
    def test_returns_correct_count_two_platforms(self, mock_decrypt):
        mock_decrypt.return_value = {"username": "admin", "password": "secret"}
        page = _mock_page()
        platforms = [_mock_platform("Portal A"), _mock_platform("Portal B")]

        tools = generate_tools(platforms, page)

        # 2 logins + 5 browser + 3 data/action = 10
        assert len(tools) == 10

    @patch("app.engine.tool_generator.decrypt_credentials")
    def test_returns_correct_count_no_platforms(self, mock_decrypt):
        page = _mock_page()

        tools = generate_tools([], page)

        # 0 logins + 5 browser + 3 data/action = 8
        assert len(tools) == 8
        mock_decrypt.assert_not_called()

    @patch("app.engine.tool_generator.decrypt_credentials")
    def test_login_tool_names_match_platforms(self, mock_decrypt):
        mock_decrypt.return_value = {"username": "u", "password": "p"}
        page = _mock_page()
        platforms = [_mock_platform("Sprout"), _mock_platform("Five9")]

        tools = generate_tools(platforms, page)

        login_tools = [t for t in tools if hasattr(t, "name") and "login" in t.name]
        names = {t.name for t in login_tools}
        assert "login_to_sprout" in names
        assert "login_to_five9" in names

    @patch("app.engine.tool_generator.decrypt_credentials")
    def test_decrypts_each_platform_credentials(self, mock_decrypt):
        mock_decrypt.return_value = {"username": "u", "password": "p"}
        page = _mock_page()
        p1 = _mock_platform("A")
        p2 = _mock_platform("B")

        generate_tools([p1, p2], page)

        assert mock_decrypt.call_count == 2
        mock_decrypt.assert_any_call(p1.credentials_encrypted)
        mock_decrypt.assert_any_call(p2.credentials_encrypted)

    @patch("app.engine.tool_generator.decrypt_credentials")
    def test_includes_generic_browser_tools(self, mock_decrypt):
        mock_decrypt.return_value = {"username": "u", "password": "p"}
        page = _mock_page()

        tools = generate_tools([_mock_platform()], page)

        tool_names = {t.name for t in tools if hasattr(t, "name")}
        assert "navigate" in tool_names
        assert "scrape_table" in tool_names
        assert "click_element" in tool_names
        assert "fill_form" in tool_names
        assert "take_screenshot" in tool_names

    @patch("app.engine.tool_generator.decrypt_credentials")
    def test_includes_data_action_tools(self, mock_decrypt):
        mock_decrypt.return_value = {"username": "u", "password": "p"}
        page = _mock_page()

        tools = generate_tools([_mock_platform()], page)

        tool_names = {t.name for t in tools if hasattr(t, "name")}
        assert "analyze_data" in tool_names
        assert "export_csv" in tool_names
        assert "send_alert" in tool_names

    @patch("app.engine.tool_generator.decrypt_credentials")
    def test_custom_output_dirs(self, mock_decrypt):
        mock_decrypt.return_value = {"username": "u", "password": "p"}
        page = _mock_page()

        tools = generate_tools(
            [_mock_platform()],
            page,
            screenshot_dir="/custom/screenshots",
            export_dir="/custom/exports",
        )

        # Should still work and return the right count
        assert len(tools) == 9
