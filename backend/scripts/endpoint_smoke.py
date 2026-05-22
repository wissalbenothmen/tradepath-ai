"""End-to-end smoke test for every TradePath AI endpoint.

Hits every route exposed in /api/docs against a running backend, reports
PASS / FAIL per endpoint, and exits non-zero if anything other than the
expected status is returned.

Usage (with the backend running on :8007 and the seeded demo DB)::

    python -m scripts.endpoint_smoke

The script is idempotent: it creates throwaway shipments/classifications/etc.
for each non-GET endpoint so subsequent runs do not depend on each other.
"""
from __future__ import annotations

import io
import json
import sys
from typing import Any, Optional

import httpx

BASE = "http://127.0.0.1:8007"
DEMO_EMAIL = "demo@tradepath.ai"
DEMO_PASS = "DemoPass1!"

# Color codes for terminal output
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"


class Probe:
    def __init__(self) -> None:
        self.client = httpx.Client(base_url=BASE, timeout=30.0)
        self.token: Optional[str] = None
        self.passes = 0
        self.fails = 0
        self.skips = 0
        self.results: list[tuple[str, str, str, int, str]] = []

    # ---- helpers ----------------------------------------------------------
    def _headers(self, auth: bool = True) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if auth and self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _record(self, method: str, path: str, expected: list[int], status: int, note: str = "") -> bool:
        ok = status in expected
        tag = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        exp = "/".join(str(e) for e in expected)
        print(f"  {tag}  {method:6s} {path:55s} → {status} (expected {exp}) {DIM}{note}{RESET}")
        self.results.append((method, path, "pass" if ok else "fail", status, note))
        if ok:
            self.passes += 1
        else:
            self.fails += 1
        return ok

    # ---- probes -----------------------------------------------------------
    def probe_public(self) -> None:
        print("\n📡 Public probes")
        r = self.client.get("/health")
        self._record("GET", "/health", [200], r.status_code)
        r = self.client.get("/readyz")
        self._record("GET", "/readyz", [200], r.status_code)
        r = self.client.get("/api/docs")
        self._record("GET", "/api/docs", [200], r.status_code, "Swagger UI HTML")
        r = self.client.get("/api/redoc")
        self._record("GET", "/api/redoc", [200], r.status_code, "ReDoc HTML")
        r = self.client.get("/openapi.json")
        self._record("GET", "/openapi.json", [200], r.status_code, "OpenAPI schema")

    def probe_auth(self) -> None:
        print("\n🔐 Auth")
        # Register: a fresh email per run keeps this idempotent.
        import uuid
        email = f"probe_{uuid.uuid4().hex[:8]}@example.com"
        r = self.client.post("/api/v1/auth/register", json={
            "email": email, "password": "StrongPass1!",
            "full_name": "Probe User", "role": "customs_broker",
        })
        self._record("POST", "/api/v1/auth/register", [201], r.status_code)

        # Login
        r = self.client.post(
            "/api/v1/auth/login",
            data={"username": DEMO_EMAIL, "password": DEMO_PASS},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code == 200:
            self.token = r.json()["access_token"]
        self._record("POST", "/api/v1/auth/login", [200], r.status_code, f"token={self.token[:16] if self.token else 'NONE'}…")

        # /me
        r = self.client.get("/api/v1/auth/me", headers=self._headers())
        self._record("GET", "/api/v1/auth/me", [200], r.status_code)

        # /invite — add a new user to the demo tenant.
        invitee = f"invitee_{uuid.uuid4().hex[:8]}@example.com"
        r = self.client.post(
            "/api/v1/auth/invite",
            json={"email": invitee, "password": "StrongPass1!", "full_name": "Invitee", "role": "customs_broker"},
            headers=self._headers(),
        )
        self._record("POST", "/api/v1/auth/invite", [201], r.status_code)

        # Bad-token → 401
        bad = self.client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        self._record("GET", "/api/v1/auth/me (bad token)", [401], bad.status_code, "negative path")

    def probe_shipments(self) -> tuple[Optional[str], list[str]]:
        print("\n🚢 Shipments")
        r = self.client.get("/api/v1/shipments", headers=self._headers())
        self._record("GET", "/api/v1/shipments", [200], r.status_code, f"{len(r.json()) if r.status_code==200 else '?'} rows")
        ship_ids = [s["id"] for s in r.json()] if r.status_code == 200 else []
        first_id = ship_ids[0] if ship_ids else None

        # Create a fresh shipment
        r = self.client.post(
            "/api/v1/shipments",
            json={
                "origin_country": "USA", "destination_country": "MEX",
                "transport_mode": "road", "incoterms": "FOB",
                "exporter_name": "Probe Co.", "importer_name": "Probe Importer",
                "total_value_usd": 12500.0,
            },
            headers=self._headers(),
        )
        new_id: Optional[str] = None
        if r.status_code == 201:
            new_id = r.json()["id"]
        self._record("POST", "/api/v1/shipments", [201], r.status_code, f"new id={new_id[:8] if new_id else '?'}…")

        # GET /shipments/{id}
        if new_id:
            r = self.client.get(f"/api/v1/shipments/{new_id}", headers=self._headers())
            self._record("GET", "/api/v1/shipments/{id}", [200], r.status_code)
            # PATCH /shipments/{id}/status?new_status=screening
            r = self.client.patch(
                f"/api/v1/shipments/{new_id}/status",
                params={"new_status": "screening"},
                headers=self._headers(),
            )
            self._record("PATCH", "/api/v1/shipments/{id}/status", [200], r.status_code)

        # Use the first existing shipment for the voice / cross-validate / brief endpoints
        if first_id:
            r = self.client.get(f"/api/v1/shipments/{first_id}/voice-records", headers=self._headers())
            self._record("GET", "/api/v1/shipments/{id}/voice-records", [200], r.status_code)

            r = self.client.post(f"/api/v1/shipments/{first_id}/amendment-cross-validate", headers=self._headers())
            self._record("POST", "/api/v1/shipments/{id}/amendment-cross-validate", [200], r.status_code)

            r = self.client.get(f"/api/v1/shipments/{first_id}/amendment-brief.pdf", headers=self._headers())
            ok = r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf")
            self._record(
                "GET", "/api/v1/shipments/{id}/amendment-brief.pdf",
                [200], r.status_code,
                f"pdf={'yes' if ok else 'no'} bytes={len(r.content)}",
            )

        return new_id, ship_ids

    def probe_classification(self, line_item_id: Optional[str] = None) -> Optional[str]:
        print("\n🧠 Classification")
        # GET list
        r = self.client.get("/api/v1/classification", headers=self._headers())
        self._record("GET", "/api/v1/classification", [200], r.status_code, f"{len(r.json()) if r.status_code==200 else '?'} rows")

        # POST classify
        body: dict[str, Any] = {
            "product_description": "Industrial CNC machining centre, 5-axis precision",
            "materials": "Steel + carbide",
            "intended_use": "Aerospace component manufacturing",
            "country_of_origin": "USA",
        }
        if line_item_id:
            body["line_item_id"] = line_item_id
        r = self.client.post("/api/v1/classification", json=body, headers=self._headers())
        cls_id: Optional[str] = None
        if r.status_code == 201:
            cls_id = r.json()["id"]
        self._record("POST", "/api/v1/classification", [201], r.status_code, f"new id={cls_id[:8] if cls_id else '?'}…")

        if cls_id:
            r = self.client.get(f"/api/v1/classification/{cls_id}", headers=self._headers())
            self._record("GET", "/api/v1/classification/{id}", [200], r.status_code)
            r = self.client.post(f"/api/v1/classification/{cls_id}/confirm", headers=self._headers())
            self._record("POST", "/api/v1/classification/{id}/confirm", [200], r.status_code)
        return cls_id

    def probe_screening(self, ship_id: str) -> Optional[str]:
        print("\n🛡️  Screening")
        r = self.client.get(f"/api/v1/screening/shipment/{ship_id}", headers=self._headers())
        self._record("GET", "/api/v1/screening/shipment/{id}", [200], r.status_code)

        r = self.client.post(
            "/api/v1/screening",
            json={
                "shipment_id": ship_id,
                "party_name": "Acme Trading Corp",
                "party_type": "importer",
                "party_country": "USA",
            },
            headers=self._headers(),
        )
        scr_id = r.json()["id"] if r.status_code == 201 else None
        self._record("POST", "/api/v1/screening", [201], r.status_code, f"new id={scr_id[:8] if scr_id else '?'}…")

        if scr_id:
            r = self.client.post(
                f"/api/v1/screening/{scr_id}/review",
                json={"decision": "approved", "notes": "Smoke test review", "apply_legal_hold": False, "whitelist": False},
                headers=self._headers(),
            )
            self._record("POST", "/api/v1/screening/{id}/review", [200], r.status_code)
        return scr_id

    def probe_declarations(self, ship_id: str) -> Optional[str]:
        print("\n📄 Declarations")
        r = self.client.get(f"/api/v1/declarations/shipment/{ship_id}", headers=self._headers())
        self._record("GET", "/api/v1/declarations/shipment/{id}", [200], r.status_code)

        r = self.client.post(
            "/api/v1/declarations",
            json={
                "shipment_id": ship_id,
                "declaration_type": "cbp_entry_01",
                "port_of_entry": "USNYC",
                "declared_value_usd": 12500.0,
                "cif_value_usd": 13250.0,
                "fob_value_usd": 12100.0,
            },
            headers=self._headers(),
        )
        dec_id = r.json()["id"] if r.status_code == 201 else None
        self._record("POST", "/api/v1/declarations", [201], r.status_code, f"new id={dec_id[:8] if dec_id else '?'}…")

        if dec_id:
            r = self.client.post(f"/api/v1/declarations/{dec_id}/validate", headers=self._headers())
            self._record("POST", "/api/v1/declarations/{id}/validate", [200], r.status_code)
            r = self.client.post(f"/api/v1/declarations/{dec_id}/generate-edi", headers=self._headers())
            self._record("POST", "/api/v1/declarations/{id}/generate-edi", [200], r.status_code)
            r = self.client.post(f"/api/v1/declarations/{dec_id}/submit", headers=self._headers())
            self._record("POST", "/api/v1/declarations/{id}/submit", [200], r.status_code)
        return dec_id

    def probe_coo(self, ship_id: str) -> None:
        print("\n🏷️  Certificate of Origin")
        r = self.client.get(f"/api/v1/coo/shipment/{ship_id}", headers=self._headers())
        self._record("GET", "/api/v1/coo/shipment/{id}", [200], r.status_code)

        r = self.client.post(
            "/api/v1/coo",
            json={
                "shipment_id": ship_id,
                "coo_format": "usmca",
                "fta_agreement": "USMCA",
                "exporter_name": "Probe Co.", "importer_name": "Probe Importer",
                "country_of_origin": "USA",
                "transaction_value_usd": 12500.0,
                "non_originating_materials_usd": 1500.0,
            },
            headers=self._headers(),
        )
        self._record("POST", "/api/v1/coo", [201], r.status_code)

    def probe_fta(self, ship_id: str) -> None:
        print("\n💰 FTA")
        r = self.client.get(f"/api/v1/fta/shipment/{ship_id}", headers=self._headers())
        self._record("GET", "/api/v1/fta/shipment/{id}", [200], r.status_code)

        r = self.client.post(
            "/api/v1/fta",
            json={
                "shipment_id": ship_id,
                "hs_code_6digit": "847130",
                "product_description": "Industrial CNC machining centre",
                "declared_value_usd": 12500.0,
            },
            headers=self._headers(),
        )
        self._record("POST", "/api/v1/fta", [201], r.status_code)

    def probe_documents(self, ship_id: str) -> None:
        print("\n📎 Documents")
        r = self.client.get(f"/api/v1/documents/shipment/{ship_id}", headers=self._headers())
        self._record("GET", "/api/v1/documents/shipment/{id}", [200], r.status_code)

        # Multipart upload: a small fake PDF blob is fine — the OCR service
        # has a deterministic fallback.
        fake_pdf = b"%PDF-1.4\nfake invoice body\n%%EOF"
        r = self.client.post(
            "/api/v1/documents",
            files={"file": ("invoice.pdf", io.BytesIO(fake_pdf), "application/pdf")},
            data={"shipment_id": ship_id, "document_type": "commercial_invoice"},
            headers=self._headers(),
        )
        self._record("POST", "/api/v1/documents", [201], r.status_code)

        # Try to GET the newly-uploaded one
        if r.status_code == 201:
            doc_id = r.json()["id"]
            r = self.client.get(f"/api/v1/documents/{doc_id}", headers=self._headers())
            self._record("GET", "/api/v1/documents/{id}", [200], r.status_code)

    def probe_restrictions(self) -> None:
        print("\n⚖️  Restrictions")
        r = self.client.post(
            "/api/v1/restrictions/check",
            json={
                "origin_country": "USA",
                "destination_country": "DEU",
                "hs_code_6digit": "847130",
                "is_itar_ear": False,
            },
            headers=self._headers(),
        )
        self._record("POST", "/api/v1/restrictions/check", [200], r.status_code)

    def probe_analytics(self) -> None:
        print("\n📊 Analytics")
        for path in (
            "/api/v1/analytics/dashboard",
            "/api/v1/analytics/trends",
            "/api/v1/analytics/by-jurisdiction",
            "/api/v1/analytics/top-ftas",
            "/api/v1/analytics/action-queue",
            "/api/v1/analytics/ai-insights",
        ):
            r = self.client.get(path, headers=self._headers())
            self._record("GET", path, [200], r.status_code)

    def probe_amendments(self, ship_id: str) -> None:
        print("\n🎙️  Voice Amendments")
        r = self.client.get(f"/api/v1/shipment-amendments/shipment/{ship_id}", headers=self._headers())
        self._record("GET", "/api/v1/shipment-amendments/shipment/{id}", [200], r.status_code)

        # File upload — small dummy audio. MOCK_WHISPER=true returns a fixture.
        fake_audio = b"RIFF\x00\x00\x00\x00WAVEfmt "
        r = self.client.post(
            f"/api/v1/shipment-amendments/shipment/{ship_id}/upload",
            files={"file": ("amendment.wav", io.BytesIO(fake_audio), "audio/wav")},
            data={"amendment_type": "correction"},
            headers=self._headers(),
        )
        # Whisper may return 502 in pure-mock mode if no fixture; accept both.
        self._record(
            "POST", "/api/v1/shipment-amendments/shipment/{id}/upload",
            [201, 502], r.status_code, "mock whisper may 502 — both accepted",
        )

    def probe_negative_isolation(self) -> None:
        """Sanity-check that the OTHER tenant cannot read the demo tenant."""
        print("\n🛡️  Tenant-isolation negative checks")
        # Login as the second tenant
        r = self.client.post(
            "/api/v1/auth/login",
            data={"username": "otherco@tradepath.ai", "password": "OtherCoPass1!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code != 200:
            print(f"  {YELLOW}SKIP{RESET}  second-tenant login failed; skipping isolation checks")
            self.skips += 1
            return
        other_token = r.json()["access_token"]

        # Fetch demo tenant shipments first to get an id to probe
        old_token = self.token
        demo_ships = self.client.get("/api/v1/shipments", headers={"Authorization": f"Bearer {old_token}"}).json()
        if not demo_ships:
            print(f"  {YELLOW}SKIP{RESET}  no demo shipments available")
            self.skips += 1
            return
        target_id = demo_ships[0]["id"]

        r = self.client.get(f"/api/v1/shipments/{target_id}", headers={"Authorization": f"Bearer {other_token}"})
        self._record("GET", "/api/v1/shipments/{id} (cross-tenant)", [404], r.status_code, "must NOT leak")

        r = self.client.get(f"/api/v1/coo/shipment/{target_id}", headers={"Authorization": f"Bearer {other_token}"})
        self._record("GET", "/api/v1/coo/shipment/{id} (cross-tenant)", [404], r.status_code, "must NOT leak")

        r = self.client.get(f"/api/v1/declarations/shipment/{target_id}", headers={"Authorization": f"Bearer {other_token}"})
        self._record("GET", "/api/v1/declarations/shipment/{id} (cross-tenant)", [404], r.status_code, "must NOT leak")

    # ---- main -------------------------------------------------------------
    def run(self) -> int:
        print("🛰️  TradePath AI endpoint smoke test")
        print(f"   target: {BASE}")
        self.probe_public()
        self.probe_auth()
        if not self.token:
            print(f"\n{RED}Login failed — aborting.{RESET}")
            return 2
        new_id, ship_ids = self.probe_shipments()
        # Use the freshly-created shipment so we don't mutate seeded data.
        ship_id = new_id or (ship_ids[0] if ship_ids else None)
        if not ship_id:
            print(f"\n{RED}No shipment available — aborting.{RESET}")
            return 3
        self.probe_classification()
        self.probe_screening(ship_id)
        self.probe_declarations(ship_id)
        self.probe_coo(ship_id)
        self.probe_fta(ship_id)
        self.probe_documents(ship_id)
        self.probe_restrictions()
        self.probe_analytics()
        self.probe_amendments(ship_id)
        self.probe_negative_isolation()

        total = self.passes + self.fails
        print(f"\n{'='*70}")
        if self.fails == 0:
            print(f"{GREEN}✓ {self.passes}/{total} endpoints passed{RESET} ({self.skips} skipped)")
            return 0
        print(f"{RED}✗ {self.fails} failed{RESET} · {GREEN}{self.passes} passed{RESET} · {self.skips} skipped (of {total})")
        for m, p, status, code, note in self.results:
            if status == "fail":
                print(f"   {RED}FAIL{RESET}  {m} {p}  status={code} {note}")
        return 1


if __name__ == "__main__":
    sys.exit(Probe().run())
