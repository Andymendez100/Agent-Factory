"""Tests for browser automation tools.

Each make_*_tool() factory is tested with a mocked Playwright page to verify
correct async calls and return values.
"""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock external deps not installed locally (playwright, langchain_core)
# ---------------------------------------------------------------------------
for mod in (
    "playwright",
    "playwright.async_api",
    "langchain_core",
    "langchain_core.tools",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Provide a real-enough @tool decorator so our factories produce callables.
# The real langchain @tool wraps the function; we just need the coroutine to
# stay callable and preserve its name/description.
_real_tool_mod = sys.modules["langchain_core.tools"]


def _fake_tool(name_or_func=None, *args, **kwargs):
    """Minimal stand-in for langchain_core.tools.tool.

    Supports both ``@tool`` and ``@tool("custom_name")`` usage.
    """
    def decorator(fn):
        fn.name = name if name else fn.__name__
        fn.description = fn.__doc__ or ""
        return fn

    if callable(name_or_func):
        # @tool without arguments
        name = None
        return decorator(name_or_func)
    else:
        # @tool("custom_name")
        name = name_or_func
        return decorator


_real_tool_mod.tool = _fake_tool

from app.tools.browser import (
    make_click_tool,
    make_fill_form_tool,
    make_login_tool,
    make_navigate_tool,
    make_scrape_table_tool,
    make_screenshot_tool,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_page(**overrides) -> AsyncMock:
    """Create a mocked Playwright Page with common async methods."""
    page = AsyncMock()
    page.url = overrides.get("url", "http://localhost:8001/dashboard")
    page.goto = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.screenshot = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.eval_on_selector_all = AsyncMock()
    return page


# ---------------------------------------------------------------------------
# make_login_tool
# ---------------------------------------------------------------------------

class TestMakeLoginTool:
    @pytest.mark.asyncio
    async def test_login_tool_navigates_and_fills(self):
        page = _mock_page(url="http://portal.example.com/dashboard")
        tool_fn = make_login_tool(
            platform_name="Test Portal",
            login_url="http://portal.example.com/login",
            username="admin",
            password="secret",
            selectors={
                "username_field": "#user",
                "password_field": "#pass",
                "submit_button": "#login-btn",
            },
            page=page,
        )
        result = await tool_fn()
        page.goto.assert_awaited_once_with(
            "http://portal.example.com/login", wait_until="domcontentloaded"
        )
        page.fill.assert_any_await("#user", "admin")
        page.fill.assert_any_await("#pass", "secret")
        page.click.assert_awaited_once_with("#login-btn")
        assert "Successfully logged in" in result
        assert "Test Portal" in result

    def test_login_tool_name_is_sanitized(self):
        page = _mock_page()
        tool_fn = make_login_tool(
            platform_name="BPO Employee Portal",
            login_url="http://x",
            username="u",
            password="p",
            selectors={"username_field": "#u", "password_field": "#p", "submit_button": "#s"},
            page=page,
        )
        assert tool_fn.name == "login_to_bpo_employee_portal"


# ---------------------------------------------------------------------------
# make_navigate_tool
# ---------------------------------------------------------------------------

class TestMakeNavigateTool:
    @pytest.mark.asyncio
    async def test_navigate_calls_goto(self):
        page = _mock_page(url="http://example.com/target")
        tool_fn = make_navigate_tool(page)
        result = await tool_fn("http://example.com/target")
        page.goto.assert_awaited_once_with(
            "http://example.com/target", wait_until="domcontentloaded"
        )
        assert "Navigated to" in result


# ---------------------------------------------------------------------------
# make_scrape_table_tool
# ---------------------------------------------------------------------------

class TestMakeScrapeTableTool:
    @pytest.mark.asyncio
    async def test_scrape_returns_json_with_headers_and_rows(self):
        page = _mock_page()
        page.eval_on_selector_all.side_effect = [
            ["Name", "Hours"],  # headers
            [["Alice", "8"], ["Bob", "7"]],  # rows
        ]
        tool_fn = make_scrape_table_tool(page)
        result = await tool_fn("table.employees")
        data = json.loads(result)
        assert data["headers"] == ["Name", "Hours"]
        assert len(data["rows"]) == 2
        assert data["rows"][0] == {"Name": "Alice", "Hours": "8"}

    @pytest.mark.asyncio
    async def test_scrape_empty_table(self):
        page = _mock_page()
        page.eval_on_selector_all.side_effect = [[], []]
        tool_fn = make_scrape_table_tool(page)
        result = await tool_fn("table.empty")
        data = json.loads(result)
        assert data["headers"] == []
        assert data["rows"] == []


# ---------------------------------------------------------------------------
# make_click_tool
# ---------------------------------------------------------------------------

class TestMakeClickTool:
    @pytest.mark.asyncio
    async def test_click_calls_page_click(self):
        page = _mock_page(url="http://example.com/next")
        tool_fn = make_click_tool(page)
        result = await tool_fn("a.nav-link")
        page.click.assert_awaited_once_with("a.nav-link")
        assert "Clicked element" in result


# ---------------------------------------------------------------------------
# make_fill_form_tool
# ---------------------------------------------------------------------------

class TestMakeFillFormTool:
    @pytest.mark.asyncio
    async def test_fill_form_fills_multiple_fields(self):
        page = _mock_page()
        tool_fn = make_fill_form_tool(page)
        fields = json.dumps({"#name": "Alice", "#email": "alice@test.com"})
        result = await tool_fn(fields)
        page.fill.assert_any_await("#name", "Alice")
        page.fill.assert_any_await("#email", "alice@test.com")
        assert "2 field(s)" in result


# ---------------------------------------------------------------------------
# make_screenshot_tool
# ---------------------------------------------------------------------------

class TestMakeScreenshotTool:
    @pytest.mark.asyncio
    async def test_screenshot_saves_to_output_dir(self, tmp_path):
        page = _mock_page()
        tool_fn = make_screenshot_tool(page, output_dir=str(tmp_path))
        result = await tool_fn("test_shot")
        page.screenshot.assert_awaited_once()
        call_kwargs = page.screenshot.call_args[1]
        assert call_kwargs["full_page"] is True
        assert str(tmp_path) in call_kwargs["path"]
        assert "test_shot" in call_kwargs["path"]
        assert "Screenshot saved to" in result
