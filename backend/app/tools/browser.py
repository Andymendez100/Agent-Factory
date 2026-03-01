"""Browser automation tools for the ReAct agent.

Each ``make_*_tool()`` factory accepts a Playwright *page* (and optionally
platform config) and returns a LangChain tool that the LLM can invoke.
The tool closures capture the page so the agent can drive the browser
through natural-language tool calls.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from playwright.async_api import Page


# ---------------------------------------------------------------------------
# Per-platform login tool
# ---------------------------------------------------------------------------

def make_login_tool(
    platform_name: str,
    login_url: str,
    username: str,
    password: str,
    selectors: dict,
    page: Page,
):
    """Create a login tool for a specific platform.

    Parameters
    ----------
    platform_name : str
        Human-readable name (used in the tool name / docstring).
    login_url : str
        Full URL of the login page.
    username, password : str
        Decrypted credentials.
    selectors : dict
        Must contain ``username_field``, ``password_field``, ``submit_button``
        CSS selectors.
    page : Page
        Playwright page instance shared across this run.
    """
    safe_name = re.sub(r"[^a-z0-9_]", "_", platform_name.lower().strip())

    @tool(f"login_to_{safe_name}")
    async def login_to_platform() -> str:
        f"""Log in to {platform_name}.

        Navigates to the login page, fills in the stored credentials, and
        submits the form.  Returns a confirmation message on success.
        """
        await page.goto(login_url, wait_until="domcontentloaded")
        await page.fill(selectors["username_field"], username)
        await page.fill(selectors["password_field"], password)
        await page.click(selectors["submit_button"])
        await page.wait_for_load_state("networkidle")
        return f"Successfully logged in to {platform_name}. Current URL: {page.url}"

    # Override docstring since f-string in decorator doesn't propagate
    login_to_platform.description = (
        f"Log in to {platform_name}. Navigates to the login page, fills "
        "credentials, and submits the form."
    )

    return login_to_platform


# ---------------------------------------------------------------------------
# Generic browser tools
# ---------------------------------------------------------------------------

def make_navigate_tool(page: Page):
    """Create a tool that navigates the browser to a given URL."""

    @tool
    async def navigate(url: str) -> str:
        """Navigate the browser to a URL.

        Use this to visit any page.  Returns the final URL after navigation
        (which may differ due to redirects).
        """
        await page.goto(url, wait_until="domcontentloaded")
        return f"Navigated to {page.url}"

    return navigate


def make_scrape_table_tool(page: Page):
    """Create a tool that extracts an HTML table as JSON."""

    @tool
    async def scrape_table(selector: str) -> str:
        """Extract an HTML table matching a CSS selector and return it as JSON.

        Args:
            selector: CSS selector for the <table> element (e.g. "table.employees").

        Returns a JSON object with ``headers`` (list of column names) and
        ``rows`` (list of dicts keyed by header).
        """
        headers = await page.eval_on_selector_all(
            f"{selector} thead th",
            "elements => elements.map(el => el.innerText.trim())",
        )
        raw_rows = await page.eval_on_selector_all(
            f"{selector} tbody tr",
            """rows => rows.map(row =>
                Array.from(row.querySelectorAll('td'))
                    .map(td => td.innerText.trim())
            )""",
        )
        rows = [dict(zip(headers, cells)) for cells in raw_rows]
        return json.dumps({"headers": headers, "rows": rows})

    return scrape_table


def make_click_tool(page: Page):
    """Create a tool that clicks an element by CSS selector."""

    @tool
    async def click_element(selector: str) -> str:
        """Click an element matching a CSS selector.

        Args:
            selector: CSS selector for the element to click.
        """
        await page.click(selector)
        await page.wait_for_load_state("domcontentloaded")
        return f"Clicked element '{selector}'. Current URL: {page.url}"

    return click_element


def make_fill_form_tool(page: Page):
    """Create a tool that fills multiple form fields."""

    @tool
    async def fill_form(fields: str) -> str:
        """Fill form fields on the current page.

        Args:
            fields: A JSON string mapping CSS selectors to values,
                    e.g. ``{{"#name": "Alice", "#email": "alice@example.com"}}``.
        """
        parsed = json.loads(fields)
        for selector, value in parsed.items():
            await page.fill(selector, value)
        filled = ", ".join(parsed.keys())
        return f"Filled {len(parsed)} field(s): {filled}"

    return fill_form


def make_screenshot_tool(page: Page, output_dir: str = "/tmp/screenshots"):
    """Create a tool that takes a browser screenshot.

    Parameters
    ----------
    page : Page
        Playwright page instance.
    output_dir : str
        Directory where screenshots are saved.
    """

    @tool
    async def take_screenshot(name: str) -> str:
        """Take a screenshot of the current browser page.

        Args:
            name: A short descriptive name for the screenshot (no extension).

        Returns the file path of the saved PNG screenshot.
        """
        os.makedirs(output_dir, exist_ok=True)
        ts = int(time.time())
        filename = f"{name}_{ts}.png"
        filepath = os.path.join(output_dir, filename)
        await page.screenshot(path=filepath, full_page=True)
        return f"Screenshot saved to {filepath}"

    return take_screenshot
