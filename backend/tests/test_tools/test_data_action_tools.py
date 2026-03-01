"""Tests for data and action tools (analysis, export CSV, send alert)."""

import csv
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock external deps not installed locally
# ---------------------------------------------------------------------------
for mod in (
    "langchain_core",
    "langchain_core.tools",
    "langchain_openai",
):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Fake @tool decorator — same pattern as test_browser.py
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

from app.tools.analysis import make_analyze_tool
from app.tools.export import make_export_csv_tool
from app.tools.alert import make_send_alert_tool


# ---------------------------------------------------------------------------
# make_analyze_tool tests
# ---------------------------------------------------------------------------

class TestMakeAnalyzeTool:
    @pytest.mark.asyncio
    async def test_analyze_calls_llm_with_data_and_question(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Active time is 85%, below threshold.")
        )

        with patch("app.tools.analysis.ChatOpenAI", return_value=mock_llm):
            tool_fn = make_analyze_tool()
            result = await tool_fn(
                data='[{"employee": "Alice", "active_pct": 85}]',
                question="Is active time below 90%?",
            )

        assert "85%" in result
        mock_llm.ainvoke.assert_awaited_once()
        prompt_arg = mock_llm.ainvoke.call_args[0][0]
        assert "Alice" in prompt_arg
        assert "below 90%" in prompt_arg

    @pytest.mark.asyncio
    async def test_analyze_returns_llm_content(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="All metrics are on target.")
        )

        with patch("app.tools.analysis.ChatOpenAI", return_value=mock_llm):
            tool_fn = make_analyze_tool()
            result = await tool_fn(data="some data", question="summary?")

        assert result == "All metrics are on target."


# ---------------------------------------------------------------------------
# make_export_csv_tool tests
# ---------------------------------------------------------------------------

class TestMakeExportCsvTool:
    @pytest.mark.asyncio
    async def test_export_list_of_dicts(self, tmp_path):
        tool_fn = make_export_csv_tool(output_dir=str(tmp_path))
        data = json.dumps([
            {"name": "Alice", "hours": 8},
            {"name": "Bob", "hours": 7},
        ])
        result = await tool_fn(data=data, filename="report")

        assert "2 rows" in result
        # Verify file was created
        csv_files = list(tmp_path.glob("report_*.csv"))
        assert len(csv_files) == 1

        with open(csv_files[0]) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_export_dict_with_rows_key(self, tmp_path):
        tool_fn = make_export_csv_tool(output_dir=str(tmp_path))
        data = json.dumps({
            "headers": ["name", "hours"],
            "rows": [{"name": "Carol", "hours": 6}],
        })
        result = await tool_fn(data=data, filename="detail")
        assert "1 rows" in result

    @pytest.mark.asyncio
    async def test_export_empty_rows_returns_error(self, tmp_path):
        tool_fn = make_export_csv_tool(output_dir=str(tmp_path))
        data = json.dumps([])
        result = await tool_fn(data=data, filename="empty")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_export_invalid_shape_returns_error(self, tmp_path):
        tool_fn = make_export_csv_tool(output_dir=str(tmp_path))
        data = json.dumps({"not_rows": "bad"})
        result = await tool_fn(data=data, filename="bad")
        assert "Error" in result


# ---------------------------------------------------------------------------
# make_send_alert_tool tests
# ---------------------------------------------------------------------------

class TestMakeSendAlertTool:
    @pytest.mark.asyncio
    async def test_alert_logs_when_smtp_not_configured(self):
        """When SMTP_USER is empty, the tool logs instead of sending."""
        with patch("app.tools.alert.settings") as mock_settings:
            mock_settings.SMTP_USER = ""
            mock_settings.SMTP_PASSWORD = ""
            tool_fn = make_send_alert_tool()
            result = await tool_fn(
                subject="Low Activity",
                body="Employee #3 is at 80%",
                recipient="manager@example.com",
            )

        assert "Alert logged" in result
        assert "manager@example.com" in result

    @pytest.mark.asyncio
    async def test_alert_sends_email_when_smtp_configured(self):
        """When SMTP is configured, the tool sends an actual email."""
        mock_smtp_instance = MagicMock()
        mock_smtp_cls = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.tools.alert.settings") as mock_settings,
            patch("app.tools.alert.smtplib.SMTP", mock_smtp_cls),
        ):
            mock_settings.SMTP_USER = "sender@example.com"
            mock_settings.SMTP_PASSWORD = "pass123"
            mock_settings.SMTP_HOST = "smtp.example.com"
            mock_settings.SMTP_PORT = 587

            tool_fn = make_send_alert_tool()
            result = await tool_fn(
                subject="Alert",
                body="test body",
                recipient="boss@example.com",
            )

        assert "Email sent" in result
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("sender@example.com", "pass123")
        mock_smtp_instance.send_message.assert_called_once()
