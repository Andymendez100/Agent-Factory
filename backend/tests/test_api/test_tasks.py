import pytest


SAMPLE_PLATFORM = {
    "name": "Test Portal",
    "base_url": "https://portal.example.com",
    "login_url": "https://portal.example.com/login",
    "credentials": {"username": "admin", "password": "secret"},
    "login_selectors": {"username_field": "#email", "password_field": "#pass", "submit_button": "#btn"},
}


async def _create_platform(client, name="Test Portal"):
    payload = {**SAMPLE_PLATFORM, "name": name}
    resp = await client.post("/api/platforms", json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_task(client):
    pid = await _create_platform(client)
    resp = await client.post("/api/tasks", json={
        "name": "Morning KPI Check",
        "goal": "Check active time for employee #1",
        "platform_ids": [pid],
        "constraints": {"threshold": 0.9},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Morning KPI Check"
    assert data["goal"] == "Check active time for employee #1"
    assert len(data["platforms"]) == 1
    assert data["platforms"][0]["id"] == pid
    assert data["constraints"] == {"threshold": 0.9}


@pytest.mark.asyncio
async def test_create_task_invalid_platform(client):
    resp = await client.post("/api/tasks", json={
        "name": "Bad Task",
        "goal": "Do nothing",
        "platform_ids": ["00000000-0000-0000-0000-000000000000"],
    })
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_tasks(client):
    pid = await _create_platform(client, "List Portal")
    await client.post("/api/tasks", json={
        "name": "Task A", "goal": "Goal A", "platform_ids": [pid],
    })
    resp = await client.get("/api/tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(t["name"] == "Task A" for t in data)


@pytest.mark.asyncio
async def test_get_task_by_id(client):
    pid = await _create_platform(client, "Get Portal")
    create_resp = await client.post("/api/tasks", json={
        "name": "Get Task", "goal": "Goal", "platform_ids": [pid],
    })
    task_id = create_resp.json()["id"]

    resp = await client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == task_id
    assert len(resp.json()["platforms"]) == 1


@pytest.mark.asyncio
async def test_get_task_not_found(client):
    resp = await client.get("/api/tasks/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_task(client):
    pid = await _create_platform(client, "Update Portal")
    create_resp = await client.post("/api/tasks", json={
        "name": "Old Name", "goal": "Old Goal", "platform_ids": [pid],
    })
    task_id = create_resp.json()["id"]

    resp = await client.put(f"/api/tasks/{task_id}", json={
        "name": "New Name", "goal": "New Goal",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["goal"] == "New Goal"


@pytest.mark.asyncio
async def test_delete_task(client):
    pid = await _create_platform(client, "Delete Portal")
    create_resp = await client.post("/api/tasks", json={
        "name": "Doomed Task", "goal": "Bye", "platform_ids": [pid],
    })
    task_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/tasks/{task_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 404
