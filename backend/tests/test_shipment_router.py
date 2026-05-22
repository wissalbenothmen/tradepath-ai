from __future__ import annotations
import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_shipment(client: AsyncClient, broker_token: str):
    resp = await client.post(
        "/api/v1/shipments",
        json={
            "origin_country": "CN",
            "destination_country": "US",
            "transport_mode": "sea",
            "incoterms": "CIF",
            "exporter_name": "Shanghai Electronics Co",
            "consignee_name": "US Importer LLC",
            "total_value_usd": 50000.0,
            "currency": "USD",
        },
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["origin_country"] == "CN"
    assert data["destination_country"] == "US"
    assert data["status"] == "draft"
    assert data["reference_number"].startswith("TP-")


@pytest.mark.asyncio
async def test_list_shipments(client: AsyncClient, broker_token: str):
    await client.post(
        "/api/v1/shipments",
        json={"origin_country": "MX", "destination_country": "US"},
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    resp = await client.get(
        "/api/v1/shipments",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_shipment_not_found(client: AsyncClient, broker_token: str):
    resp = await client.get(
        f"/api/v1/shipments/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_shipment_status(client: AsyncClient, broker_token: str):
    create_resp = await client.post(
        "/api/v1/shipments",
        json={"origin_country": "DE", "destination_country": "US"},
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    shipment_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/shipments/{shipment_id}/status",
        params={"new_status": "screening"},
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "screening"


@pytest.mark.asyncio
async def test_unauthenticated_request(client: AsyncClient):
    resp = await client.get("/api/v1/shipments")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_analytics_dashboard(client: AsyncClient, broker_token: str):
    resp = await client.get(
        "/api/v1/analytics/dashboard",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "shipments" in data
    assert "screening" in data
    assert "classification" in data


@pytest.mark.asyncio
async def test_restriction_check_clear(client: AsyncClient, broker_token: str):
    resp = await client.post(
        "/api/v1/restrictions/check",
        json={
            "origin_country": "DE",
            "destination_country": "US",
            "hs_code_6digit": "847130",
            "is_itar_ear": False,
        },
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CLEAR"


@pytest.mark.asyncio
async def test_restriction_check_prohibited(client: AsyncClient, broker_token: str):
    resp = await client.post(
        "/api/v1/restrictions/check",
        json={
            "origin_country": "KP",
            "destination_country": "US",
            "hs_code_6digit": "847130",
            "is_itar_ear": False,
        },
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PROHIBITED"
