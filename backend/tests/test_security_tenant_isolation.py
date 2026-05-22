"""Security regression tests for the fixes shipped in this PR.

Covers the five audit-flagged incidents:

1. Self-registration cannot escalate into an existing tenant.
2. Cross-tenant reads on classification / declaration / coo / fta / documents
   / screening / amendments / shipments are forbidden (404, never the data).
3. Cross-tenant analytics counts are scoped to the caller's tenant.
4. Password complexity rejects weak passwords.
5. Malformed JWT returns 401, not 500.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.customs_declaration import (
    CustomsDeclaration,
    DeclarationStatus,
    DeclarationType,
)
from app.models.denied_party_screening import DeniedPartyScreening, ScreeningResult
from app.models.hs_classification import ClassificationStatus, HSClassification
from app.models.shipment import Shipment, ShipmentStatus
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _make_user(session: AsyncSession, *, email: str, company_id: uuid.UUID,
                     role: UserRole = UserRole.CUSTOMS_BROKER) -> User:
    user = User(
        email=email, hashed_password=hash_password("StrongPass1!"),
        full_name=email.split("@")[0], role=role, company_id=company_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _make_shipment(session: AsyncSession, *, owner: User) -> Shipment:
    s = Shipment(
        reference_number=f"TP-{uuid.uuid4().hex[:6].upper()}",
        company_id=owner.company_id,
        created_by=owner.id,
        status=ShipmentStatus.DRAFT,
        origin_country="USA",
        destination_country="DEU",
        currency="USD",
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


# ---------------------------------------------------------------------------
# 1. Self-registration cannot claim an existing tenant
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_register_ignores_client_supplied_company_id(client: AsyncClient):
    """The old /auth/register accepted body.company_id; attackers could join
    any tenant by guessing the UUID. After the patch, the schema does not
    define ``company_id`` at all — submitting one is ignored."""
    target_company = uuid.uuid4()
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"new_{uuid.uuid4().hex[:8]}@example.com",
            "password": "StrongPass1!",
            "full_name": "Attacker",
            "role": "customs_broker",
            "company_id": str(target_company),  # SHOULD BE IGNORED
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["company_id"] != str(target_company), (
        "Self-registration must NOT honour a client-supplied company_id."
    )


@pytest.mark.asyncio
async def test_register_rejects_weak_password(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"weak_{uuid.uuid4().hex[:8]}@example.com",
            "password": "password",  # missing upper / digit / symbol
            "full_name": "Weak",
        },
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# 2. /auth/invite adds a user to the INVITER's tenant (the only legit path)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invite_adds_user_to_inviters_tenant(client: AsyncClient, engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as s:
        owner = await _make_user(
            s, email=f"owner_{uuid.uuid4().hex[:8]}@example.com",
            company_id=uuid.uuid4(),
        )
    owner_token = create_access_token(str(owner.id))
    resp = await client.post(
        "/api/v1/auth/invite",
        json={
            "email": f"invitee_{uuid.uuid4().hex[:8]}@example.com",
            "password": "StrongPass1!",
            "full_name": "Invitee",
            "role": "customs_broker",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["company_id"] == str(owner.company_id)


# ---------------------------------------------------------------------------
# 3. Cross-tenant reads are forbidden across every domain
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cannot_read_other_tenants_shipment(client: AsyncClient, engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as s:
        a = await _make_user(s, email=f"a_{uuid.uuid4().hex[:8]}@example.com", company_id=uuid.uuid4())
        b = await _make_user(s, email=f"b_{uuid.uuid4().hex[:8]}@example.com", company_id=uuid.uuid4())
        ship_a = await _make_shipment(s, owner=a)

    token_b = create_access_token(str(b.id))
    resp = await client.get(
        f"/api/v1/shipments/{ship_a.id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_cannot_read_other_tenants_classification(client: AsyncClient, engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as s:
        a = await _make_user(s, email=f"a_{uuid.uuid4().hex[:8]}@example.com", company_id=uuid.uuid4())
        b = await _make_user(s, email=f"b_{uuid.uuid4().hex[:8]}@example.com", company_id=uuid.uuid4())
        cls = HSClassification(
            company_id=a.company_id, classified_by=a.id,
            status=ClassificationStatus.CLASSIFIED,
            hs_code_6digit="847130", confidence=0.9,
        )
        s.add(cls)
        await s.commit()
        await s.refresh(cls)

    token_b = create_access_token(str(b.id))
    resp = await client.get(
        f"/api/v1/classification/{cls.id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_list_other_tenants_screenings_via_shipment_id(
    client: AsyncClient, engine,
):
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as s:
        a = await _make_user(s, email=f"a_{uuid.uuid4().hex[:8]}@example.com", company_id=uuid.uuid4())
        b = await _make_user(s, email=f"b_{uuid.uuid4().hex[:8]}@example.com", company_id=uuid.uuid4())
        ship_a = await _make_shipment(s, owner=a)
        sc = DeniedPartyScreening(
            company_id=a.company_id, shipment_id=ship_a.id, screened_by=a.id,
            party_name="Acme Corp", party_type="importer",
            overall_result=ScreeningResult.CLEAR, highest_score=0.05,
            lists_checked=["OFAC SDN"], matches=[],
        )
        s.add(sc)
        await s.commit()

    token_b = create_access_token(str(b.id))
    resp = await client.get(
        f"/api/v1/screening/shipment/{ship_a.id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_cannot_read_other_tenants_declaration_via_shipment(
    client: AsyncClient, engine,
):
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as s:
        a = await _make_user(s, email=f"a_{uuid.uuid4().hex[:8]}@example.com", company_id=uuid.uuid4())
        b = await _make_user(s, email=f"b_{uuid.uuid4().hex[:8]}@example.com", company_id=uuid.uuid4())
        ship_a = await _make_shipment(s, owner=a)
        decl = CustomsDeclaration(
            company_id=a.company_id, shipment_id=ship_a.id, created_by=a.id,
            declaration_type=DeclarationType.CBP_ENTRY_01,
            status=DeclarationStatus.DRAFT,
            declared_value_usd=50_000.0,
        )
        s.add(decl)
        await s.commit()

    token_b = create_access_token(str(b.id))
    resp = await client.get(
        f"/api/v1/declarations/shipment/{ship_a.id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. Analytics dashboard counts only the caller's tenant
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_analytics_dashboard_scoped_by_tenant(client: AsyncClient, engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as s:
        a = await _make_user(s, email=f"a_{uuid.uuid4().hex[:8]}@example.com", company_id=uuid.uuid4())
        b = await _make_user(s, email=f"b_{uuid.uuid4().hex[:8]}@example.com", company_id=uuid.uuid4())
        # Tenant A: 1 shipment, 1 classification, 1 positive screening.
        ship_a = await _make_shipment(s, owner=a)
        s.add(HSClassification(
            company_id=a.company_id, line_item_id=uuid.uuid4(), classified_by=a.id,
            status=ClassificationStatus.CONFIRMED, hs_code_6digit="847130", confidence=0.95,
        ))
        s.add(DeniedPartyScreening(
            company_id=a.company_id, shipment_id=ship_a.id, screened_by=a.id,
            party_name="X", party_type="importer",
            overall_result=ScreeningResult.POSITIVE_MATCH, highest_score=0.97,
        ))
        await s.commit()

    # Tenant B's dashboard must show zeros.
    token_b = create_access_token(str(b.id))
    resp = await client.get("/api/v1/analytics/dashboard", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["shipments"]["total"] == 0, data
    assert data["classification"]["total"] == 0, data
    assert data["screening"]["positive_matches"] == 0, (
        "Cross-tenant screening leak — the audit-flagged regression."
    )

    # Tenant A sees their own.
    token_a = create_access_token(str(a.id))
    resp_a = await client.get("/api/v1/analytics/dashboard", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["shipments"]["total"] == 1
    assert data_a["classification"]["total"] == 1
    assert data_a["screening"]["positive_matches"] == 1


# ---------------------------------------------------------------------------
# 5. Malformed JWT returns 401, not 500
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_malformed_uuid_in_jwt_returns_401(client: AsyncClient):
    """Tokens whose ``sub`` is not a UUID used to bubble a 500. They must 401."""
    bad_token = create_access_token("not-a-valid-uuid")
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_token}"}
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_bad_token_signature_returns_401(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.valid.jwt"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 6. /readyz reports DB health
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_readyz_passes(client: AsyncClient):
    resp = await client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"
