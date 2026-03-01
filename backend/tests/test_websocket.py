"""Tests for the WebSocket endpoint and Redis pub/sub helpers.

Tests verify:
- WebSocket receives and forwards Redis pub/sub messages
- run_complete event causes graceful WebSocket close
- publish_step / publish_run_complete send correct payloads
- get_redis lazy singleton behaviour
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


# ---------------------------------------------------------------------------
# redis_pubsub unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_redis_returns_client():
    """get_redis creates and returns an async Redis client."""
    with patch("app.services.redis_pubsub.aioredis") as mock_aioredis:
        mock_client = MagicMock()
        mock_aioredis.from_url.return_value = mock_client

        # Reset the singleton
        import app.services.redis_pubsub as mod
        mod._redis_client = None

        client = mod.get_redis()
        assert client is mock_client
        mock_aioredis.from_url.assert_called_once()

        # Second call returns same instance (singleton)
        client2 = mod.get_redis()
        assert client2 is mock_client
        assert mock_aioredis.from_url.call_count == 1

        # Cleanup
        mod._redis_client = None


@pytest.mark.asyncio
async def test_get_redis_singleton_reuses_client():
    """get_redis returns the same Redis instance on subsequent calls."""
    import app.services.redis_pubsub as mod

    fake_client = MagicMock()
    mod._redis_client = fake_client

    result = mod.get_redis()
    assert result is fake_client

    # Cleanup
    mod._redis_client = None


@pytest.mark.asyncio
async def test_publish_step_sends_to_correct_channel():
    """publish_step publishes JSON payload to run:{run_id} channel."""
    mock_redis = AsyncMock()

    with patch("app.services.redis_pubsub.get_redis", return_value=mock_redis):
        from app.services.redis_pubsub import publish_step

        await publish_step("abc-123", {"step_index": 0, "step_type": "agent_thinking"})

        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "run:abc-123"

        payload = json.loads(call_args[0][1])
        assert payload["step_index"] == 0
        assert payload["step_type"] == "agent_thinking"


@pytest.mark.asyncio
async def test_publish_run_complete_sends_terminal_event():
    """publish_run_complete publishes a run_complete message."""
    mock_redis = AsyncMock()

    with patch("app.services.redis_pubsub.get_redis", return_value=mock_redis):
        from app.services.redis_pubsub import publish_run_complete

        await publish_run_complete(
            "abc-123", final_status="completed", final_answer="All done."
        )

        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "run:abc-123"

        payload = json.loads(call_args[0][1])
        assert payload["type"] == "run_complete"
        assert payload["status"] == "completed"
        assert payload["final_answer"] == "All done."


@pytest.mark.asyncio
async def test_publish_run_complete_with_error():
    """publish_run_complete includes error field for failed runs."""
    mock_redis = AsyncMock()

    with patch("app.services.redis_pubsub.get_redis", return_value=mock_redis):
        from app.services.redis_pubsub import publish_run_complete

        await publish_run_complete(
            "abc-123", final_status="failed", error="Browser crashed"
        )

        call_args = mock_redis.publish.call_args
        payload = json.loads(call_args[0][1])
        assert payload["type"] == "run_complete"
        assert payload["status"] == "failed"
        assert payload["error"] == "Browser crashed"
        assert payload["final_answer"] is None


# ---------------------------------------------------------------------------
# WebSocket endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_websocket_receives_step_messages():
    """WebSocket forwards Redis pub/sub messages to the client."""
    step_msg = json.dumps({
        "step_index": 0,
        "step_type": "agent_thinking",
        "agent_reasoning": "Let me check the data.",
    })

    complete_msg = json.dumps({"type": "run_complete", "status": "completed"})

    call_count = 0

    async def fake_get_message(ignore_subscribe_messages=True, timeout=0.5):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"type": "message", "data": step_msg.encode()}
        elif call_count == 2:
            return {"type": "message", "data": complete_msg.encode()}
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = fake_get_message
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()

    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = mock_pubsub

    with patch("app.api.websocket.get_redis", return_value=mock_redis):
        from app.main import app
        client = TestClient(app)

        with client.websocket_connect("/ws/runs/test-run-id") as ws:
            # Should receive the step message
            data1 = ws.receive_text()
            parsed1 = json.loads(data1)
            assert parsed1["step_type"] == "agent_thinking"
            assert parsed1["agent_reasoning"] == "Let me check the data."

            # Should receive run_complete
            data2 = ws.receive_text()
            parsed2 = json.loads(data2)
            assert parsed2["type"] == "run_complete"


@pytest.mark.asyncio
async def test_websocket_subscribes_to_correct_channel():
    """WebSocket subscribes to the run-specific Redis channel."""
    complete_msg = json.dumps({"type": "run_complete", "status": "completed"})

    call_count = 0

    async def fake_get_message(ignore_subscribe_messages=True, timeout=0.5):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"type": "message", "data": complete_msg.encode()}
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = fake_get_message
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()

    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = mock_pubsub

    with patch("app.api.websocket.get_redis", return_value=mock_redis):
        from app.main import app
        client = TestClient(app)

        with client.websocket_connect("/ws/runs/my-run-uuid"):
            pass  # Just connect and let it complete

        mock_pubsub.subscribe.assert_called_once_with("run:my-run-uuid")
        mock_pubsub.unsubscribe.assert_called_once_with("run:my-run-uuid")


@pytest.mark.asyncio
async def test_websocket_handles_bytes_data():
    """WebSocket decodes bytes from Redis before sending to client."""
    msg = json.dumps({"step_index": 0, "step_type": "tool_call", "tool_name": "navigate"})
    complete_msg = json.dumps({"type": "run_complete", "status": "completed"})

    call_count = 0

    async def fake_get_message(ignore_subscribe_messages=True, timeout=0.5):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"type": "message", "data": msg.encode("utf-8")}
        elif call_count == 2:
            return {"type": "message", "data": complete_msg.encode("utf-8")}
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = fake_get_message
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()

    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = mock_pubsub

    with patch("app.api.websocket.get_redis", return_value=mock_redis):
        from app.main import app
        client = TestClient(app)

        with client.websocket_connect("/ws/runs/test-123") as ws:
            data = ws.receive_text()
            parsed = json.loads(data)
            assert parsed["tool_name"] == "navigate"
            # Consume run_complete
            ws.receive_text()
