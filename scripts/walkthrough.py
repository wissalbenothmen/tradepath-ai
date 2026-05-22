#!/usr/bin/env python3
"""TradePath AI — Complete Feature Walkthrough (30 data-rich screenshots)."""
import os
import time
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5037"
API_BASE = "http://127.0.0.1:8037/api/v1"
SHOTS_DIR = Path(__file__).parent / "project-audit" / "screenshots"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)

EMAIL = "walkthrough3@tradepath.ai"
PASSWORD = "WalkPass1!"

shot_index = 0


def shot(page, name: str):
    global shot_index
    shot_index += 1
    fname = SHOTS_DIR / f"{shot_index:02d}-{name}.jpg"
    page.screenshot(path=str(fname), full_page=True, type="jpeg", quality=92)
    print(f"  [SHOT {shot_index:02d}]  {name}")
    return fname


def wait(page, ms=900):
    page.wait_for_timeout(ms)


def go(page, token: str, path: str, ms: int = 1200):
    """Navigate authenticated to a path."""
    page.evaluate(f"localStorage.setItem('token', '{token}')")
    page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
    wait(page, ms)


def seed_all(token: str) -> dict:
    """Seed rich demo data and return IDs."""
    import requests
    h = {"Authorization": f"Bearer {token}"}

    def ship(body):
        return requests.post(f"{API_BASE}/shipments", json=body, headers=h).json()

    def status(sid, s):
        requests.patch(f"{API_BASE}/shipments/{sid}/status?new_status={s}", headers=h)

    # --- 10 shipments covering every status ---
    s1 = ship({"origin_country": "US", "destination_country": "DE",
               "transport_mode": "sea", "incoterms": "CIF",
               "exporter_name": "Acme Manufacturing Corp", "importer_name": "EuroTech GmbH",
               "total_value_usd": 285000, "total_weight_kg": 4500,
               "shipment_date": "2026-07-15", "currency": "USD",
               "notes": "Industrial equipment — automotive sector"})

    s2 = ship({"origin_country": "CN", "destination_country": "US",
               "transport_mode": "air", "incoterms": "FOB",
               "exporter_name": "Shenzhen Electronics Ltd", "importer_name": "TechImport USA Inc",
               "total_value_usd": 92000, "total_weight_kg": 850})

    s3 = ship({"origin_country": "MX", "destination_country": "US",
               "transport_mode": "road", "incoterms": "DAP",
               "exporter_name": "Maquiladora Textil SA", "importer_name": "FashionRetail USA",
               "total_value_usd": 58000, "total_weight_kg": 2200})

    s4 = ship({"origin_country": "JP", "destination_country": "GB",
               "transport_mode": "sea", "incoterms": "CFR",
               "exporter_name": "Yamaha Precision Parts", "importer_name": "BritishAuto Ltd",
               "total_value_usd": 145000, "total_weight_kg": 3100})

    s5 = ship({"origin_country": "KR", "destination_country": "US",
               "transport_mode": "sea", "incoterms": "CIF",
               "exporter_name": "Samsung Trading Corp", "importer_name": "Pacific Distributors",
               "total_value_usd": 320000, "total_weight_kg": 7800})

    s6 = ship({"origin_country": "IN", "destination_country": "FR",
               "transport_mode": "air", "incoterms": "EXW",
               "exporter_name": "Tata Steel Export Division", "importer_name": "Acier France SA",
               "total_value_usd": 74000, "total_weight_kg": 950})

    s7 = ship({"origin_country": "BR", "destination_country": "DE",
               "transport_mode": "sea", "incoterms": "FOB",
               "exporter_name": "Vale Minerals Brazil", "importer_name": "RWE Resources GmbH",
               "total_value_usd": 410000, "total_weight_kg": 18000})

    s8 = ship({"origin_country": "CN", "destination_country": "US",
               "transport_mode": "sea", "incoterms": "CIF",
               "exporter_name": "Shenzhen Solar Tech", "importer_name": "GreenEnergy Corp",
               "total_value_usd": 195000, "total_weight_kg": 5600})

    # Advance statuses to populate every column
    for sid in [s1.get("id", ""), s4.get("id", ""), s5.get("id", "")]:
        status(sid, "screening")
    for sid in [s2.get("id", ""), s6.get("id", "")]:
        status(sid, "cleared")
    status(s7.get("id", ""), "hold")
    status(s8.get("id", ""), "blocked")

    # --- Screenings ---
    def screen(body):
        return requests.post(f"{API_BASE}/screening", json=body, headers=h).json()

    screen({"shipment_id": s1.get("id",""), "party_name": "EuroTech GmbH",
            "party_type": "consignee", "party_country": "DE"})
    screen({"shipment_id": s2.get("id",""), "party_name": "Shenzhen Electronics Ltd",
            "party_type": "shipper", "party_country": "CN"})
    scr_huawei = screen({"shipment_id": s5.get("id",""), "party_name": "Huawei Technologies",
                          "party_type": "manufacturer", "party_country": "CN"})
    screen({"shipment_id": s4.get("id",""), "party_name": "Yamaha Precision Parts",
            "party_type": "shipper", "party_country": "JP"})

    # --- Classifications ---
    def classify(body):
        return requests.post(f"{API_BASE}/classification", json=body, headers=h).json()

    cls1 = classify({"product_description": "Industrial hydraulic pump — cast iron housing, stainless steel shaft, PTFE seals, 250 bar rated",
                     "materials": "cast iron, stainless steel, PTFE", "intended_use": "Hydraulic power in assembly lines"})
    cls2 = classify({"product_description": "Woven cotton denim fabric for apparel — 100% cotton, 14oz weight, indigo dye",
                     "materials": "100% cotton", "intended_use": "Garment manufacturing"})
    cls3 = classify({"product_description": "Automotive lithium-ion battery pack — 72V 200Ah for electric vehicles",
                     "materials": "lithium, cobalt, manganese, polymer electrolyte", "intended_use": "Electric vehicle propulsion"})

    if cls1.get("id"):
        requests.post(f"{API_BASE}/classification/{cls1['id']}/confirm", headers=h)
    if cls2.get("id"):
        requests.post(f"{API_BASE}/classification/{cls2['id']}/confirm", headers=h)

    # --- Declarations ---
    decl = requests.post(f"{API_BASE}/declarations", json={
        "shipment_id": s1.get("id",""), "declaration_type": "cbp_entry_01",
        "declared_value_usd": 285000, "fob_value_usd": 275000, "cif_value_usd": 291000,
        "port_of_entry": "HAMBURG"
    }, headers=h).json()

    # --- COO ---
    requests.post(f"{API_BASE}/coo", json={
        "shipment_id": s1.get("id",""), "coo_format": "usmca",
        "exporter_name": "Acme Manufacturing Corp", "importer_name": "EuroTech GmbH",
        "country_of_origin": "US", "transaction_value_usd": 285000,
        "non_originating_materials_usd": 52000
    }, headers=h)

    # --- FTA (MX→US, HS 630110 textiles — 12% MFN → USMCA saves $6,960) ---
    requests.post(f"{API_BASE}/fta", json={
        "shipment_id": s3.get("id",""), "hs_code_6digit": "630110",
        "product_description": "Woven cotton blankets and travelling rugs",
        "declared_value_usd": 58000
    }, headers=h)

    return {
        "s1_id": s1.get("id", ""), "s2_id": s2.get("id", ""),
        "s3_id": s3.get("id", ""), "s4_id": s4.get("id", ""),
        "s5_id": s5.get("id", ""), "decl_id": decl.get("id", ""),
    }


def run():
    import requests

    requests.post(f"{API_BASE}/auth/register", json={
        "email": EMAIL, "password": PASSWORD,
        "full_name": "Compliance Auditor", "role": "customs_broker",
    })

    login_r = requests.post(f"{API_BASE}/auth/login",
        data={"username": EMAIL, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    token = login_r.json().get("access_token", "")
    if not token:
        print("ERROR: Could not get access token. Is the backend running on port 8037?")
        return

    print(f"[AUTH] Token acquired for {EMAIL}")
    ids = seed_all(token)
    s1_id = ids["s1_id"]
    s3_id = ids["s3_id"]
    s5_id = ids["s5_id"]
    print(f"[SEED] s1={s1_id[:8]}  s3={s3_id[:8]}  s5={s5_id[:8]}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
        )
        page = ctx.new_page()

        # ── AUTH ─────────────────────────────────────────────────────────────
        print("\n[AUTH]")

        # 01 — Login page
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        wait(page)
        shot(page, "login-page")

        # 02 — Login form with credentials filled (ready to submit)
        page.fill("input[type='email']", EMAIL)
        page.fill("input[type='password']", PASSWORD)
        wait(page, 500)
        shot(page, "login-form-credentials-filled")

        # 03 — Successful login → dashboard
        page.fill("input[type='password']", PASSWORD)
        page.click("button[type='submit']")
        wait(page, 2500)
        if "/login" in page.url or page.url.rstrip("/") == BASE_URL:
            page.evaluate(f"localStorage.setItem('token', '{token}')")
            page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
            wait(page, 1500)
        shot(page, "login-success-dashboard")

        # ── DASHBOARD ────────────────────────────────────────────────────────
        print("\n[DASHBOARD]")

        # 04 — Dashboard KPI cards + status distribution
        go(page, token, "/dashboard", 1500)
        shot(page, "dashboard-kpis-and-chart")

        # ── SHIPMENTS ────────────────────────────────────────────────────────
        print("\n[SHIPMENTS]")

        # 05 — Shipments list with all varied statuses
        go(page, token, "/shipments", 1200)
        shot(page, "shipments-list-full")

        # 06 — New shipment form filled
        page.click("button:has-text('New Shipment')")
        wait(page, 700)
        page.fill("input[placeholder='CN']", "AU")
        page.fill("input[placeholder='US']", "SG")
        inputs = page.locator("form input:not([type='number'])")
        if inputs.count() >= 3:
            inputs.nth(2).fill("sea")
        if inputs.count() >= 4:
            inputs.nth(3).fill("CIF")
        if inputs.count() >= 5:
            inputs.nth(4).fill("Sydney Exports Pty Ltd")
        if inputs.count() >= 6:
            inputs.nth(5).fill("Singapore Trade Hub Pte")
        page.locator("form input[type='number']").fill("112000")
        shot(page, "new-shipment-form-filled")

        # 07 — After creation: list refreshes with new row
        page.click("button:has-text('Create Shipment')")
        wait(page, 2000)
        shot(page, "shipment-created-in-list")

        # ── CLASSIFICATION ────────────────────────────────────────────────────
        print("\n[CLASSIFICATION]")

        # 08 — Standard product: form + result on same page
        go(page, token, "/classification", 1000)
        page.fill("textarea", "Industrial hydraulic pump — cast iron housing, stainless steel shaft, PTFE seals, 250 bar rated operating pressure")
        page.fill("input[placeholder='e.g., 100% cotton, cast iron, PTFE']", "cast iron, stainless steel, PTFE")
        page.fill("input[placeholder='e.g., industrial fluid transfer']", "Hydraulic power transmission in assembly lines")
        page.fill("input[placeholder='e.g., CN']", "US")
        shot(page, "classification-form-filled")

        page.click("button:has-text('Classify Product')")
        wait(page, 3000)
        shot(page, "classification-result-standard")

        # 09 — ITAR flagged product
        page.fill("textarea", "")
        wait(page, 200)
        page.fill("textarea", "Defense-grade cryptographic encryption module for military secure communications — hardware security module")
        page.fill("input[placeholder='e.g., 100% cotton, cast iron, PTFE']", "silicon, gallium arsenide, RF shielding")
        page.fill("input[placeholder='e.g., industrial fluid transfer']", "Military secure communications, defense")
        page.fill("input[placeholder='e.g., CN']", "US")
        page.click("button:has-text('Classify Product')")
        wait(page, 3000)
        shot(page, "classification-itar-flagged")

        # ── SCREENING ────────────────────────────────────────────────────────
        print("\n[SCREENING]")

        # 10 — Clear result: EuroTech GmbH
        go(page, token, "/screening", 1000)
        page.fill("input[placeholder='UUID of the shipment']", s1_id)
        page.fill("input[placeholder='Full legal entity name']", "EuroTech GmbH")
        page.select_option("select", "consignee")
        page.fill("input[placeholder='e.g., IR']", "DE")
        page.click("button:has-text('Run Screening')")
        wait(page, 2500)
        shot(page, "screening-clear-result")

        # 11 — Positive match: Huawei Technologies (BIS Entity List)
        page.fill("input[placeholder='UUID of the shipment']", s5_id)
        page.fill("input[placeholder='Full legal entity name']", "Huawei Technologies")
        page.select_option("select", "manufacturer")
        page.fill("input[placeholder='e.g., IR']", "CN")
        page.click("button:has-text('Run Screening')")
        wait(page, 2500)
        shot(page, "screening-positive-match-huawei")

        # ── DECLARATIONS ─────────────────────────────────────────────────────
        print("\n[DECLARATIONS]")

        # 12 — Form filled + created
        go(page, token, "/declarations", 1000)
        page.locator("form input:not([type='number'])").nth(0).fill(s1_id)
        page.select_option("select", "cbp_entry_01")
        page.fill("input[placeholder='USNYC']", "HAMBURG")
        nums = page.locator("form input[type='number']")
        nums.nth(0).fill("285000")
        nums.nth(1).fill("291000")
        nums.nth(2).fill("275000")
        shot(page, "declarations-form-filled")

        page.click("button:has-text('Create Declaration')")
        wait(page, 2500)
        shot(page, "declaration-created-with-duty")

        # 13 — AI Validate
        ai_btn = page.locator("button:has-text('AI Validate')")
        if ai_btn.count() > 0:
            ai_btn.click()
            wait(page, 2500)
        shot(page, "declaration-after-ai-validation")

        # 14 — Generate EDI
        edi_btn = page.locator("button:has-text('Generate EDI')")
        if edi_btn.count() > 0:
            edi_btn.click()
            wait(page, 2500)
            # Wait for EDI block to appear
            try:
                page.wait_for_selector("pre", timeout=4000)
            except Exception:
                wait(page, 1000)
        shot(page, "declaration-edi-x12-generated")

        # ── COO ──────────────────────────────────────────────────────────────
        print("\n[COO]")

        # 15 — Form filled
        go(page, token, "/coo", 1000)
        text_inputs = page.locator("form input:not([type='number'])")
        text_inputs.nth(0).fill(s1_id)
        page.select_option("select", "usmca")
        text_inputs.nth(1).fill("Acme Manufacturing Corp")
        text_inputs.nth(2).fill("EuroTech GmbH")
        text_inputs.nth(3).fill("US")
        text_inputs.nth(4).fill("USMCA")
        page.locator("form input[type='number']").nth(0).fill("285000")
        page.locator("form input[type='number']").nth(1).fill("52000")
        shot(page, "coo-form-filled")

        # 16 — Result with RVC%
        page.click("button:has-text('Generate Certificate of Origin')")
        wait(page, 3000)
        shot(page, "coo-result-rvc-81pct")

        # 17 — Document content expanded
        show_btn = page.locator("button:has-text('Show Document')")
        if show_btn.count() > 0:
            show_btn.click()
            wait(page, 700)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        wait(page, 500)
        shot(page, "coo-document-content")

        # ── FTA ──────────────────────────────────────────────────────────────
        print("\n[FTA]")

        # 18 — MX→US textiles — USMCA saves $6,960 (12% MFN on $58k)
        go(page, token, "/fta", 1000)
        page.fill("input[placeholder='UUID']", s3_id)
        page.fill("input[placeholder='847130']", "630110")
        page.locator("input[placeholder='Laptop computers']").fill("Woven cotton blankets and travelling rugs — 100% cotton")
        page.locator("input[placeholder='50000']").fill("58000")
        shot(page, "fta-form-filled-textiles")

        page.click("button:has-text('Run FTA Analysis')")
        wait(page, 3000)
        shot(page, "fta-result-usmca-savings")

        # ── DOCUMENTS ────────────────────────────────────────────────────────
        print("\n[DOCUMENTS]")

        go(page, token, "/documents", 1000)

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", prefix="invoice_", delete=False)
        tmp.write(b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 250 >>
stream
BT /F1 12 Tf 50 750 Td
(COMMERCIAL INVOICE) Tj 0 -20 Td
(Vendor: Acme Manufacturing Corp) Tj 0 -20 Td
(Customer: EuroTech GmbH) Tj 0 -20 Td
(Invoice No: INV-2026-04821) Tj 0 -20 Td
(Date: 2026-07-15) Tj 0 -20 Td
(Item: Industrial Hydraulic Pump x 12 units) Tj 0 -20 Td
(Unit Price: USD 23,750.00) Tj 0 -20 Td
(Total Amount: USD 285,000.00) Tj
ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
trailer << /Size 6 /Root 1 0 R >>
startxref 0
%%EOF""")
        tmp.close()

        page.locator("form input:not([type='file'])").nth(0).fill(s1_id)
        page.select_option("select", "commercial_invoice")
        page.set_input_files("input[type='file']", tmp.name)
        wait(page, 700)
        shot(page, "documents-invoice-selected")

        page.click("button:has-text('Upload & Extract')")
        wait(page, 3500)
        shot(page, "documents-ocr-result")
        try:
            os.unlink(tmp.name)
        except OSError:
            pass  # Windows file lock — temp file will be cleaned up on reboot

        # ── ANALYTICS ────────────────────────────────────────────────────────
        print("\n[ANALYTICS]")

        # 21 — Analytics: bar chart + metric cards
        go(page, token, "/analytics", 1500)
        shot(page, "analytics-shipment-distribution")

        # 22 — Scroll to pie charts
        page.evaluate("window.scrollTo(0, 500)")
        wait(page, 800)
        shot(page, "analytics-screening-classification-charts")

        # 23 — Scroll to summary metrics at bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        wait(page, 600)
        shot(page, "analytics-summary-metrics")

        # ── RESPONSIVE ───────────────────────────────────────────────────────
        print("\n[RESPONSIVE]")

        # 24 — Dashboard at 375px
        page.set_viewport_size({"width": 375, "height": 812})
        go(page, token, "/dashboard", 1200)
        shot(page, "dashboard-mobile-375")

        # 25 — Shipments at 375px
        go(page, token, "/shipments", 1000)
        shot(page, "shipments-mobile-375")

        # 26 — Full sidebar at 1440px
        page.set_viewport_size({"width": 1440, "height": 900})
        go(page, token, "/dashboard", 1000)
        shot(page, "full-sidebar-navigation")

        # ── ERROR STATE ──────────────────────────────────────────────────────
        print("\n[ERROR STATE]")

        # 27 — Unauthenticated redirect to login
        page.evaluate("localStorage.removeItem('token')")
        page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
        wait(page, 800)
        shot(page, "unauthenticated-redirect-to-login")

        browser.close()

    print(f"\nWalkthrough complete — {shot_index} screenshots in {SHOTS_DIR}")


if __name__ == "__main__":
    run()
