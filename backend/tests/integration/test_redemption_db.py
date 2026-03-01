"""Integration tests for C redemption approval persistence.

Tests: request → pending list → approve/reject → balance changes.
Charter reference: §5 (C赎回)
Requires MySQL connection.
"""

import pytest
from httpx import AsyncClient


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _fund_c_via_income(client: AsyncClient, parent_token: str, child_id: int):
    """Fund accounts via income endpoint (default split: A 15%, B 30%, C 55%).

    Posting 2000.00 yuan income gives C ~1100.00 yuan.
    """
    resp = await client.post(
        "/api/v1/income",
        json={"amount": "2000.00", "description": "测试收入", "child_id": child_id},
        headers=_auth(parent_token),
    )
    assert resp.status_code == 200


class TestRedemptionApproveFlow:
    """Full approve flow: child request → parent approve → balances update."""

    @pytest.mark.asyncio
    async def test_full_approve_flow(self, async_client: AsyncClient, seeded_child):
        parent_token = seeded_child["parent_token"]
        child_token = seeded_child["child_token"]
        child_id = seeded_child["child_id"]
        await _fund_c_via_income(async_client, parent_token, child_id)

        # Child requests redemption
        req_resp = await async_client.post(
            "/api/v1/accounts/c/redemption/request",
            json={"amount": "500.00", "reason": "买书"},
            headers=_auth(child_token),
        )
        assert req_resp.status_code == 200
        req_data = req_resp.json()
        assert req_data["status"] == "pending"
        assert "id" in req_data
        request_id = req_data["id"]

        # GET pending list is non-empty
        pending_resp = await async_client.get(
            "/api/v1/accounts/c/redemption/pending",
            headers=_auth(parent_token),
        )
        assert pending_resp.status_code == 200
        pending_data = pending_resp.json()
        assert len(pending_data["requests"]) == 1
        assert pending_data["requests"][0]["id"] == request_id

        # Parent approves
        approve_resp = await async_client.post(
            "/api/v1/accounts/c/redemption/approve",
            json={"id": request_id, "approved": True},
            headers=_auth(parent_token),
        )
        assert approve_resp.status_code == 200
        result = approve_resp.json()
        assert result["status"] == "approved"
        assert result["amount"] == "500.00"
        assert result["fee"] == "50.00"
        assert result["net"] == "450.00"

        # Pending list is now empty
        pending_resp2 = await async_client.get(
            "/api/v1/accounts/c/redemption/pending",
            headers=_auth(parent_token),
        )
        assert len(pending_resp2.json()["requests"]) == 0


class TestRedemptionRejectFlow:
    """Reject flow: child request → parent reject → balances unchanged."""

    @pytest.mark.asyncio
    async def test_reject_preserves_balances(
        self, async_client: AsyncClient, seeded_child
    ):
        parent_token = seeded_child["parent_token"]
        child_token = seeded_child["child_token"]
        child_id = seeded_child["child_id"]
        await _fund_c_via_income(async_client, parent_token, child_id)

        # Get C balance before
        accts_resp = await async_client.get(
            "/api/v1/accounts",
            headers=_auth(parent_token),
            params={"child_id": child_id},
        )
        c_before = None
        for acc in accts_resp.json()["accounts"]:
            if acc["type"] == "C":
                c_before = acc["balance"]
                break

        # Child requests
        req_resp = await async_client.post(
            "/api/v1/accounts/c/redemption/request",
            json={"amount": "200.00", "reason": "想买"},
            headers=_auth(child_token),
        )
        request_id = req_resp.json()["id"]

        # Parent rejects
        reject_resp = await async_client.post(
            "/api/v1/accounts/c/redemption/approve",
            json={"id": request_id, "approved": False},
            headers=_auth(parent_token),
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "rejected"

        # C balance unchanged
        accts_resp2 = await async_client.get(
            "/api/v1/accounts",
            headers=_auth(parent_token),
            params={"child_id": child_id},
        )
        for acc in accts_resp2.json()["accounts"]:
            if acc["type"] == "C":
                assert acc["balance"] == c_before
                break


class TestRedemptionDuplicateApproval:
    """Already approved/rejected record cannot be approved again."""

    @pytest.mark.asyncio
    async def test_double_approve_returns_error(
        self, async_client: AsyncClient, seeded_child
    ):
        parent_token = seeded_child["parent_token"]
        child_token = seeded_child["child_token"]
        child_id = seeded_child["child_id"]
        await _fund_c_via_income(async_client, parent_token, child_id)

        req_resp = await async_client.post(
            "/api/v1/accounts/c/redemption/request",
            json={"amount": "100.00"},
            headers=_auth(child_token),
        )
        request_id = req_resp.json()["id"]

        # First approve
        resp1 = await async_client.post(
            "/api/v1/accounts/c/redemption/approve",
            json={"id": request_id, "approved": True},
            headers=_auth(parent_token),
        )
        assert resp1.status_code == 200

        # Second approve should fail
        resp2 = await async_client.post(
            "/api/v1/accounts/c/redemption/approve",
            json={"id": request_id, "approved": True},
            headers=_auth(parent_token),
        )
        assert resp2.status_code == 400
        assert "已处理" in resp2.json()["detail"]


class TestRedemptionAuth:
    """Auth and permission tests."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(
        self, async_client: AsyncClient
    ):
        resp = await async_client.post(
            "/api/v1/accounts/c/redemption/request",
            json={"amount": "100.00"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_pending_returns_401(
        self, async_client: AsyncClient
    ):
        resp = await async_client.get("/api/v1/accounts/c/redemption/pending")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_child_approve_returns_403(
        self, async_client: AsyncClient, seeded_child
    ):
        child_token = seeded_child["child_token"]
        resp = await async_client.post(
            "/api/v1/accounts/c/redemption/approve",
            json={"id": 999, "approved": True},
            headers=_auth(child_token),
        )
        assert resp.status_code == 403


class TestRedemptionPendingQuery:
    """Pending list query tests."""

    @pytest.mark.asyncio
    async def test_empty_pending_list(
        self, async_client: AsyncClient, seeded_child
    ):
        parent_token = seeded_child["parent_token"]
        resp = await async_client.get(
            "/api/v1/accounts/c/redemption/pending",
            headers=_auth(parent_token),
        )
        assert resp.status_code == 200
        assert resp.json()["requests"] == []

    @pytest.mark.asyncio
    async def test_pending_persists_across_requests(
        self, async_client: AsyncClient, seeded_child
    ):
        """Request then GET pending -- record should be present."""
        parent_token = seeded_child["parent_token"]
        child_token = seeded_child["child_token"]
        child_id = seeded_child["child_id"]
        await _fund_c_via_income(async_client, parent_token, child_id)

        # Child submits request
        await async_client.post(
            "/api/v1/accounts/c/redemption/request",
            json={"amount": "300.00", "reason": "测试"},
            headers=_auth(child_token),
        )

        # GET pending from parent perspective
        resp = await async_client.get(
            "/api/v1/accounts/c/redemption/pending",
            headers=_auth(parent_token),
        )
        data = resp.json()
        assert len(data["requests"]) == 1
        assert data["requests"][0]["amount"] == "300.00"
        assert data["requests"][0]["reason"] == "测试"

    @pytest.mark.asyncio
    async def test_child_sees_pending(
        self, async_client: AsyncClient, seeded_child
    ):
        """Child can also see the pending list."""
        parent_token = seeded_child["parent_token"]
        child_token = seeded_child["child_token"]
        child_id = seeded_child["child_id"]
        await _fund_c_via_income(async_client, parent_token, child_id)

        await async_client.post(
            "/api/v1/accounts/c/redemption/request",
            json={"amount": "100.00"},
            headers=_auth(child_token),
        )

        resp = await async_client.get(
            "/api/v1/accounts/c/redemption/pending",
            headers=_auth(child_token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["requests"]) == 1
