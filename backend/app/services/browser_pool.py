from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)


class BrowserPool:
    """Manages Playwright browser lifecycle for agent runs.

    Creates a single Chromium browser instance and provides isolated
    BrowserContexts for each agent run. Each context has its own
    cookies, storage, and session state.

    Usage::

        async with BrowserPool() as pool:
            context = await pool.new_context()
            page = await context.new_page()
            await page.goto("https://example.com")
            # ...
            await context.close()
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser = None

    async def start(self):
        """Launch Playwright and the Chromium browser."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
        )
        logger.info("BrowserPool started (headless=%s)", self.headless)

    async def new_context(self, **kwargs) -> BrowserContext:
        """Create an isolated browser context for an agent run.

        Each context has independent cookies, localStorage, and session.
        Caller is responsible for closing the context when done.
        """
        if not self._browser:
            raise RuntimeError(
                "BrowserPool not started. Use 'async with BrowserPool() as pool:'"
            )
        context = await self._browser.new_context(**kwargs)
        logger.debug("Created new browser context")
        return context

    async def close(self):
        """Shut down the browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("Browser closed")
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False
