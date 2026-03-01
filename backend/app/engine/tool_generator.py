"""Dynamic tool generator — transforms platform configs into LangChain tools.

This is the key piece that bridges platform configuration (stored in the DB)
with the LLM's ability to interact with those platforms via tools.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.services.crypto import decrypt_credentials
from app.tools.analysis import make_analyze_tool
from app.tools.alert import make_send_alert_tool
from app.tools.browser import (
    make_click_tool,
    make_fill_form_tool,
    make_login_tool,
    make_navigate_tool,
    make_scrape_table_tool,
    make_screenshot_tool,
)
from app.tools.export import make_export_csv_tool

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool
    from playwright.async_api import Page

    from app.models.platform import Platform

logger = logging.getLogger(__name__)


def generate_tools(
    platforms: list[Platform],
    page: Page,
    screenshot_dir: str = "/tmp/screenshots",
    export_dir: str = "/tmp/exports",
) -> list[BaseTool]:
    """Generate the full set of LangChain tools for an agent run.

    For each platform, decrypts its credentials and creates a per-platform
    login tool.  Then adds all generic browser tools (shared page) plus
    data-analysis and action tools.

    Parameters
    ----------
    platforms : list[Platform]
        Platform ORM objects with encrypted credentials.
    page : Page
        Playwright page instance shared across this run.
    screenshot_dir : str
        Directory for screenshot output.
    export_dir : str
        Directory for CSV export output.

    Returns
    -------
    list[BaseTool]
        All tools the agent can use during this run.
    """
    tools: list[BaseTool] = []

    # Per-platform login tools
    for platform in platforms:
        creds = decrypt_credentials(platform.credentials_encrypted)
        tools.append(
            make_login_tool(
                platform_name=platform.name,
                login_url=platform.login_url,
                username=creds["username"],
                password=creds["password"],
                selectors=platform.login_selectors,
                page=page,
            )
        )
        logger.info("Generated login tool for platform '%s'", platform.name)

    # Generic browser tools (shared page)
    tools.extend([
        make_navigate_tool(page),
        make_scrape_table_tool(page),
        make_click_tool(page),
        make_fill_form_tool(page),
        make_screenshot_tool(page, output_dir=screenshot_dir),
    ])

    # AI + data tools
    tools.extend([
        make_analyze_tool(),
        make_export_csv_tool(output_dir=export_dir),
        make_send_alert_tool(),
    ])

    logger.info(
        "Generated %d tools (%d platform logins + 5 browser + 3 data/action)",
        len(tools),
        len(platforms),
    )
    return tools
