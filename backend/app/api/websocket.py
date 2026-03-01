"""WebSocket endpoint for live agent run streaming.

Subscribes to a Redis pub/sub channel ``run:{run_id}`` and forwards each
JSON message to the connected WebSocket client in real time.  The Celery
worker publishes StepLog events to the same channel as the agent executes.

Protocol:
    1. Client connects to ``/ws/runs/{run_id}``
    2. Server subscribes to Redis channel ``run:{run_id}``
    3. Each published message is forwarded as a JSON text frame
    4. A message with ``"type": "run_complete"`` signals the end of the stream
    5. Server closes the WebSocket gracefully after run_complete or on disconnect
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.redis_pubsub import get_redis, CHANNEL_PREFIX

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/runs/{run_id}")
async def run_stream(websocket: WebSocket, run_id: str):
    """Stream live agent execution events to a WebSocket client."""
    await websocket.accept()

    redis = get_redis()
    pubsub = redis.pubsub()
    channel = f"{CHANNEL_PREFIX}{run_id}"

    try:
        await pubsub.subscribe(channel)
        logger.info("WS client subscribed to %s", channel)

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=0.5
            )

            if message and message["type"] == "message":
                data = message["data"]
                # Redis returns bytes; decode if needed
                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                await websocket.send_text(data)

                # Check if this is the terminal event
                try:
                    parsed = json.loads(data)
                    if parsed.get("type") == "run_complete":
                        logger.info("Run %s complete, closing WS", run_id)
                        break
                except (json.JSONDecodeError, TypeError):
                    pass
            else:
                # Yield control so we don't busy-loop
                await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info("WS client disconnected from %s", channel)
    except Exception:
        logger.exception("WS error on channel %s", channel)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
