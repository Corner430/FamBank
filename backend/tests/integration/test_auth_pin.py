"""Integration tests for PIN change/reset API endpoints.

Tests: PUT /auth/pin (change own PIN), PUT /auth/child-pin (reset child PIN).
"""

import pytest
from httpx import AsyncClient

PARENT_PIN = "parent1234"
CHILD_PIN = "child1234"


@pytest.fixture
def setup_payload():
    return {
        "parent_name": "甲方",
        "parent_pin": PARENT_PIN,
        "child_name": "乙方",
        "child_pin": CHILD_PIN,
    }


async def _setup_and_login(client: AsyncClient, setup_payload: dict, pin: str) -> str:
    """Setup users and login, returning the auth token."""
    await client.post("/api/v1/auth/setup", json=setup_payload)
    resp = await client.post("/api/v1/auth/login", json={"pin": pin})
    return resp.json()["token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestChangePinEndpoint:
    """Tests for PUT /api/v1/auth/pin."""

    @pytest.mark.asyncio
    async def test_change_pin_success(self, async_client: AsyncClient, setup_payload):
        """Parent can change own PIN with correct old PIN."""
        token = await _setup_and_login(async_client, setup_payload, PARENT_PIN)

        resp = await async_client.put(
            "/api/v1/auth/pin",
            json={"old_pin": PARENT_PIN, "new_pin": "newpin5678"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "密码修改成功"

        # Verify new PIN works for login
        login_resp = await async_client.post(
            "/api/v1/auth/login", json={"pin": "newpin5678"}
        )
        assert login_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_change_pin_wrong_old_pin(self, async_client: AsyncClient, setup_payload):
        """Wrong old PIN returns 401."""
        token = await _setup_and_login(async_client, setup_payload, PARENT_PIN)

        resp = await async_client.put(
            "/api/v1/auth/pin",
            json={"old_pin": "wrongpin", "new_pin": "newpin5678"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "原密码错误"

    @pytest.mark.asyncio
    async def test_change_pin_same_as_old(self, async_client: AsyncClient, setup_payload):
        """New PIN same as old returns 400."""
        token = await _setup_and_login(async_client, setup_payload, PARENT_PIN)

        resp = await async_client.put(
            "/api/v1/auth/pin",
            json={"old_pin": PARENT_PIN, "new_pin": PARENT_PIN},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "新密码不能与原密码相同"

    @pytest.mark.asyncio
    async def test_change_pin_unauthenticated(self, async_client: AsyncClient, setup_payload):
        """No auth token returns 401."""
        await async_client.post("/api/v1/auth/setup", json=setup_payload)

        resp = await async_client.put(
            "/api/v1/auth/pin",
            json={"old_pin": PARENT_PIN, "new_pin": "newpin5678"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_change_pin_child_forbidden(self, async_client: AsyncClient, setup_payload):
        """Child role returns 403."""
        await async_client.post("/api/v1/auth/setup", json=setup_payload)
        login_resp = await async_client.post(
            "/api/v1/auth/login", json={"pin": CHILD_PIN}
        )
        child_token = login_resp.json()["token"]

        resp = await async_client.put(
            "/api/v1/auth/pin",
            json={"old_pin": CHILD_PIN, "new_pin": "newpin5678"},
            headers=_auth_headers(child_token),
        )
        assert resp.status_code == 403


class TestResetChildPinEndpoint:
    """Tests for PUT /api/v1/auth/child-pin."""

    @pytest.mark.asyncio
    async def test_reset_child_pin_success(self, async_client: AsyncClient, setup_payload):
        """Parent can reset child PIN with correct parent PIN."""
        token = await _setup_and_login(async_client, setup_payload, PARENT_PIN)

        resp = await async_client.put(
            "/api/v1/auth/child-pin",
            json={"parent_pin": PARENT_PIN, "new_child_pin": "newchild9999"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "乙方PIN码重置成功"

        # Verify child can login with new PIN
        login_resp = await async_client.post(
            "/api/v1/auth/login", json={"pin": "newchild9999"}
        )
        assert login_resp.status_code == 200
        assert login_resp.json()["user"]["role"] == "child"

    @pytest.mark.asyncio
    async def test_reset_child_pin_wrong_parent_pin(self, async_client: AsyncClient, setup_payload):
        """Wrong parent PIN returns 401."""
        token = await _setup_and_login(async_client, setup_payload, PARENT_PIN)

        resp = await async_client.put(
            "/api/v1/auth/child-pin",
            json={"parent_pin": "wrongpin", "new_child_pin": "newchild9999"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "管理密码错误"

    @pytest.mark.asyncio
    async def test_reset_child_pin_unauthenticated(self, async_client: AsyncClient, setup_payload):
        """No auth token returns 401."""
        await async_client.post("/api/v1/auth/setup", json=setup_payload)

        resp = await async_client.put(
            "/api/v1/auth/child-pin",
            json={"parent_pin": PARENT_PIN, "new_child_pin": "newchild9999"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_reset_child_pin_child_forbidden(self, async_client: AsyncClient, setup_payload):
        """Child role returns 403."""
        await async_client.post("/api/v1/auth/setup", json=setup_payload)
        login_resp = await async_client.post(
            "/api/v1/auth/login", json={"pin": CHILD_PIN}
        )
        child_token = login_resp.json()["token"]

        resp = await async_client.put(
            "/api/v1/auth/child-pin",
            json={"parent_pin": CHILD_PIN, "new_child_pin": "newchild9999"},
            headers=_auth_headers(child_token),
        )
        assert resp.status_code == 403
