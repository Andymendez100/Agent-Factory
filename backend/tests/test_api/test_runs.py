import pytest


SAMPLE_PLATFORM = {
    "name": "Test Portal",
    "base_url": "https://portal.example.com",
    "login_url": "https://portal.example.com/login",
    "credentials": {"username": "admin", "password": "secret"},
    "login_selectors": {
        "username_field": "#email",
        "password_field": "#pass",
        "submit_button": "#btn",
    },
}


async def _create_task_with_platform(client, platform_name="Run Portal", task_name="Run Task"):
    """Helper: create a platform + task and return the task_id."""
    platform_resp = await client.post(
        "/api/platforms", json={**SAMPLE_PLATFORM, "name": platform_name}
    )
    assert platform_resp.status_code == 201
    pid = platform_resp.json()["id"]

    task_resp = await client.post(
        "/api/tasks",
        json={"name": task_name, "goal": "Check KPI data", "platform_ids": [pid]},
    )
    assert task_resp.status_code == 201
    return task_resp.json()["id"]


@pytest.mark.asyncio
async def test_trigger_run(client):
    task_id = await _create_task_with_platform(client, "Trigger Portal", "Trigger Task")
    resp = await client.post(f"/api/tasks/{task_id}/run")
    assert resp.status_code == 201
    data = resp.json()
    assert data["task_id"] == task_id
    assert data["status"] == "pending"
    assert data["steps"] == []
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_trigger_run_task_not_found(client):
    resp = await client.post("/api/tasks/00000000-0000-0000-0000-000000000000/run")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_runs(client):
    task_id = await _create_task_with_platform(client, "List Portal", "List Task")
    await client.post(f"/api/tasks/{task_id}/run")
    await client.post(f"/api/tasks/{task_id}/run")

    resp = await client.get("/api/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert all("status" in r for r in data)


@pytest.mark.asyncio
async def test_list_runs_pagination(client):
    task_id = await _create_task_with_platform(client, "Page Portal", "Page Task")
    for _ in range(3):
        await client.post(f"/api/tasks/{task_id}/run")

    resp = await client.get("/api/runs?skip=0&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = await client.get("/api/runs?skip=2&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_run_by_id(client):
    task_id = await _create_task_with_platform(client, "Get Run Portal", "Get Run Task")
    create_resp = await client.post(f"/api/tasks/{task_id}/run")
    run_id = create_resp.json()["id"]

    resp = await client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id
    assert resp.json()["task_id"] == task_id
    assert resp.json()["status"] == "pending"
    assert resp.json()["steps"] == []


@pytest.mark.asyncio
async def test_get_run_not_found(client):
    resp = await client.get("/api/runs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_pending_run(client):
    task_id = await _create_task_with_platform(client, "Cancel Portal", "Cancel Task")
    create_resp = await client.post(f"/api/tasks/{task_id}/run")
    run_id = create_resp.json()["id"]

    resp = await client.post(f"/api/runs/{run_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # Verify persisted
    resp = await client.get(f"/api/runs/{run_id}")
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_already_completed_run(client):
    """Cannot cancel a run that is not pending or running."""
    task_id = await _create_task_with_platform(client, "Done Portal", "Done Task")
    create_resp = await client.post(f"/api/tasks/{task_id}/run")
    run_id = create_resp.json()["id"]

    # Cancel it first
    await client.post(f"/api/runs/{run_id}/cancel")

    # Try cancelling again — should fail with 409
    resp = await client.post(f"/api/runs/{run_id}/cancel")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cancel_run_not_found(client):
    resp = await client.post("/api/runs/00000000-0000-0000-0000-000000000000/cancel")
    assert resp.status_code == 404
