"""Seed script to pre-configure the mock BPO portal as a platform.

Creates:
    1. A Platform record for the mock portal (name, URLs, encrypted
       credentials, login CSS selectors).
    2. A sample AgentTask linked to that platform with a realistic
       goal and constraints.

This runs at application startup (idempotent — skips if the platform
already exists) and can also be invoked standalone via:
    python -m app.db.seed
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.config import settings
from app.db.session import async_session
from app.models.agent_task import AgentTask
from app.models.platform import Platform
from app.services.crypto import encrypt_credentials

logger = logging.getLogger(__name__)

# Mock portal configuration
PLATFORM_NAME = "BPO Employee Portal"
PLATFORM_BASE_URL = "http://mock-portal:8001"
PLATFORM_LOGIN_URL = "http://mock-portal:8001/login"
PLATFORM_CREDENTIALS = {
    "username": "admin",
    "password": "demo123",
}
PLATFORM_LOGIN_SELECTORS = {
    "username_field": "#username",
    "password_field": "#password",
    "submit_button": "button[type='submit']",
}

# Sample agent task
TASK_NAME = "Check Active Time — Maria Santos"
TASK_GOAL = (
    "Log into the BPO Employee Portal, navigate to the employee directory, "
    "find Maria Santos (EMP-0001), and check her active time percentage "
    "over the last 14 days. Flag any days where active time drops below 90%. "
    "Provide a summary of her performance."
)
TASK_CONSTRAINTS = {
    "threshold": 0.90,
    "metric": "active_time_pct",
    "employee_name": "Maria Santos",
}


async def seed_demo_data() -> None:
    """Insert the demo platform and task if they don't already exist.

    This function is idempotent — safe to call on every startup.
    """
    async with async_session() as session:
        # Check if platform already exists
        stmt = select(Platform).where(Platform.name == PLATFORM_NAME)
        result = await session.execute(stmt)
        platform = result.scalar_one_or_none()

        if platform is None:
            platform = Platform(
                name=PLATFORM_NAME,
                base_url=PLATFORM_BASE_URL,
                login_url=PLATFORM_LOGIN_URL,
                credentials_encrypted=encrypt_credentials(PLATFORM_CREDENTIALS),
                login_selectors=PLATFORM_LOGIN_SELECTORS,
            )
            session.add(platform)
            await session.flush()  # Get the ID assigned
            logger.info("Seeded platform: %s", PLATFORM_NAME)
        else:
            logger.info("Platform '%s' already exists, skipping", PLATFORM_NAME)

        # Check if sample task already exists
        stmt = select(AgentTask).where(AgentTask.name == TASK_NAME)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if task is None:
            task = AgentTask(
                name=TASK_NAME,
                goal=TASK_GOAL,
                constraints=TASK_CONSTRAINTS,
            )
            task.platforms = [platform]
            session.add(task)
            logger.info("Seeded task: %s", TASK_NAME)
        else:
            logger.info("Task '%s' already exists, skipping", TASK_NAME)

        await session.commit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_demo_data())
