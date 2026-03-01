import pytest
import pytest_asyncio


SAMPLE_PLATFORM = {
    "name": "Test Portal",
    "base_url": "https://portal.example.com",
    "login_url": "https://portal.example.com/login",
    "credentials": {"username": "admin", "password": "secret"},
    "login_selectors": {
        "username_field": "#email",
        "password_field": "#password",
        "submit_button": "#login-btn",
    },
}


@pytest.mark.asyncio
async def test_create_platform(client):
    resp = await client.post("/api/platforms", json=SAMPLE_PLATFORM)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Portal"
    assert data["base_url"] == "https://portal.example.com"
    assert "credentials" not in data
    assert "credentials_encrypted" not in data
    assert "id" in data


@pytest.mark.asyncio
async def test_list_platforms(client):
    await client.post("/api/platforms", json=SAMPLE_PLATFORM)
    resp = await client.get("/api/platforms")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Test Portal"
    assert "credentials_encrypted" not in data[0]


@pytest.mark.asyncio
async def test_get_platform_by_id(client):
    create_resp = await client.post("/api/platforms", json=SAMPLE_PLATFORM)
    platform_id = create_resp.json()["id"]

    resp = await client.get(f"/api/platforms/{platform_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == platform_id
    assert "credentials_encrypted" not in resp.json()


@pytest.mark.asyncio
async def test_get_platform_not_found(client):
    resp = await client.get("/api/platforms/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_platform(client):
    create_resp = await client.post("/api/platforms", json=SAMPLE_PLATFORM)
    platform_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/platforms/{platform_id}",
        json={"name": "Updated Portal", "base_url": "https://updated.example.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Portal"
    assert resp.json()["base_url"] == "https://updated.example.com"


@pytest.mark.asyncio
async def test_delete_platform(client):
    create_resp = await client.post("/api/platforms", json=SAMPLE_PLATFORM)
    platform_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/platforms/{platform_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/platforms/{platform_id}")
    assert resp.status_code == 404
