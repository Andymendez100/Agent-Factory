"""Redis pub/sub helpers for live agent streaming.

Provides a shared async Redis client and convenience functions for
publishing StepLog events to per-run channels.

Channel naming: ``run:{run_id}``

The Celery worker calls :func:`publish_step` to push each step event, and
the WebSocket endpoint subscribes to the same channel to relay events
to the browser in real time.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "run:"

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return (and lazily create) the shared async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=False
        )
    return _redis_client


async def publish_step(run_id: str, step_data: dict[str, Any]) -> None:
    """Publish a StepLog event to the run's Redis channel.

    Parameters
    ----------
    run_id : str
        The UUID of the agent run.
    step_data : dict
        JSON-serialisable StepLog payload.
    """
    redis = get_redis()
    channel = f"{CHANNEL_PREFIX}{run_id}"
    payload = json.dumps(step_data, default=str)
    await redis.publish(channel, payload)
    logger.debug("Published step to %s", channel)


async def publish_run_complete(run_id: str, final_status: str, final_answer: str | None = None, error: str | None = None) -> None:
    """Publish a terminal ``run_complete`` event to close WS connections.

    Parameters
    ----------
    run_id : str
        The UUID of the agent run.
    final_status : str
        The final run status (e.g. "completed", "failed").
    final_answer : str | None
        The agent's final answer, if any.
    error : str | None
        Error message, if the run failed.
    """
    redis = get_redis()
    channel = f"{CHANNEL_PREFIX}{run_id}"
    payload = json.dumps({
        "type": "run_complete",
        "status": final_status,
        "final_answer": final_answer,
        "error": error,
    })
    await redis.publish(channel, payload)
    logger.info("Published run_complete to %s (status=%s)", channel, final_status)
