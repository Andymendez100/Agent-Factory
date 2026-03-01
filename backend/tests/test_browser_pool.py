import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure playwright modules exist for lazy imports (may not be installed locally)
if "playwright" not in sys.modules:
    sys.modules["playwright"] = MagicMock()
if "playwright.async_api" not in sys.modules:
    sys.modules["playwright.async_api"] = MagicMock()

from app.services.browser_pool import BrowserPool


def _mock_playwright():
    """Build a mock async_playwright() → playwright → browser → context chain."""
    mock_context = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw = AsyncMock()
    mock_pw.chromium = mock_chromium
    mock_pw.stop = AsyncMock()

    # async_playwright() returns an object with .start() that returns mock_pw
    mock_pw_cm = AsyncMock()
    mock_pw_cm.start = AsyncMock(return_value=mock_pw)

    return mock_pw_cm, mock_pw, mock_browser, mock_context


@pytest.mark.asyncio
async def test_start_and_close():
    """start() launches browser; close() shuts everything down."""
    mock_pw_cm, mock_pw, mock_browser, _ = _mock_playwright()

    with patch("playwright.async_api.async_playwright", return_value=mock_pw_cm):
        pool = BrowserPool(headless=True)
        await pool.start()

        mock_pw_cm.start.assert_awaited_once()
        mock_pw.chromium.launch.assert_awaited_once_with(headless=True)

        await pool.close()

        mock_browser.close.assert_awaited_once()
        mock_pw.stop.assert_awaited_once()
        assert pool._browser is None
        assert pool._playwright is None


@pytest.mark.asyncio
async def test_context_manager():
    """BrowserPool works as an async context manager."""
    mock_pw_cm, mock_pw, mock_browser, _ = _mock_playwright()

    with patch("playwright.async_api.async_playwright", return_value=mock_pw_cm):
        async with BrowserPool() as pool:
            assert pool._browser is not None

        mock_browser.close.assert_awaited_once()
        mock_pw.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_new_context_creates_isolated_context():
    """new_context() delegates to the browser's new_context()."""
    mock_pw_cm, mock_pw, mock_browser, mock_context = _mock_playwright()

    with patch("playwright.async_api.async_playwright", return_value=mock_pw_cm):
        async with BrowserPool() as pool:
            ctx = await pool.new_context(viewport={"width": 1280, "height": 720})

            mock_browser.new_context.assert_awaited_once_with(
                viewport={"width": 1280, "height": 720}
            )
            assert ctx is mock_context


@pytest.mark.asyncio
async def test_new_context_raises_if_not_started():
    """new_context() raises RuntimeError before start() is called."""
    pool = BrowserPool()
    with pytest.raises(RuntimeError, match="not started"):
        await pool.new_context()


@pytest.mark.asyncio
async def test_close_is_idempotent():
    """Calling close() twice does not raise."""
    mock_pw_cm, mock_pw, mock_browser, _ = _mock_playwright()

    with patch("playwright.async_api.async_playwright", return_value=mock_pw_cm):
        pool = BrowserPool()
        await pool.start()
        await pool.close()
        await pool.close()  # second call should be a no-op

        mock_browser.close.assert_awaited_once()
        mock_pw.stop.assert_awaited_once()
