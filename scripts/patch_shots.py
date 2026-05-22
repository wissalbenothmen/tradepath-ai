#!/usr/bin/env python3
"""Patch specific screenshots: login error (02) and EDI (16)."""
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5173"
API_BASE = "http://127.0.0.1:8037/api/v1"
SHOTS_DIR = Path(__file__).parent / "project-audit" / "screenshots"

EMAIL = "walkthrough3@tradepath.ai"
PASSWORD = "WalkPass1!"


def login_api():
    r = requests.post(f"{API_BASE}/auth/login",
        data={"username": EMAIL, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    return r.json().get("access_token", "")


def get_shipment_id(token):
    h = {"Authorization": f"Bearer {token}"}
    ships = requests.get(f"{API_BASE}/shipments", headers=h).json()
    for s in ships:
        if s.get("origin_country") == "US" and s.get("destination_country") == "DE":
            return s["id"], s.get("exporter_name", "")
    return "", ""


def shot(page, fname):
    page.screenshot(path=str(SHOTS_DIR / fname), full_page=True, type="jpeg", quality=92)
    print(f"  [SHOT] {fname}")


def run():
    token = login_api()
    ship_id, exporter = get_shipment_id(token)
    print(f"Ship ID: {ship_id[:8]}... exporter={exporter}")
    h = {"Authorization": f"Bearer {token}"}

    # Pre-create a declaration and generate EDI via API
    decl = requests.post(f"{API_BASE}/declarations", json={
        "shipment_id": ship_id,
        "declaration_type": "cbp_entry_01",
        "declared_value_usd": 285000,
        "fob_value_usd": 275000,
        "cif_value_usd": 291000,
        "port_of_entry": "HAMBURG",
    }, headers=h).json()
    decl_id = decl.get("id", "")
    print(f"Decl ID: {decl_id[:8]}...")

    # Test EDI via API
    edi_r = requests.post(f"{API_BASE}/declarations/{decl_id}/generate-edi", headers=h).json()
    has_edi = bool(edi_r.get("edi_content"))
    print(f"EDI API works: {has_edi}, content starts: {str(edi_r.get('edi_content',''))[:40]}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
        )
        page = ctx.new_page()

        # ── PATCH 02: Login error screenshot ─────────────────────────────
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.wait_for_timeout(500)

        # Fill email + password — show the form ready to submit
        page.fill("input[type='email']", EMAIL)
        page.fill("input[type='password']", PASSWORD)
        page.wait_for_timeout(500)
        shot(page, "02-login-form-credentials-filled.jpg")

        # ── PATCH 16: EDI screenshot ───────────────────────────────────────
        page.evaluate(f"localStorage.setItem('token', '{token}')")
        page.goto(f"{BASE_URL}/declarations", wait_until="networkidle")
        page.wait_for_timeout(1200)

        # Fill the form with the ship_id
        page.locator("form input:not([type='number'])").nth(0).fill(ship_id)
        page.select_option("select", "cbp_entry_01")
        page.fill("input[placeholder='USNYC']", "HAMBURG")
        nums = page.locator("form input[type='number']")
        nums.nth(0).fill("285000")
        nums.nth(1).fill("291000")
        nums.nth(2).fill("275000")

        page.click("button:has-text('Create Declaration')")
        page.wait_for_timeout(2500)

        # Click Generate EDI and wait for the pre block
        edi_btn = page.locator("button:has-text('Generate EDI')")
        if edi_btn.count() > 0:
            edi_btn.click()
            try:
                page.wait_for_selector("pre", timeout=6000)
                page.wait_for_timeout(500)
            except Exception:
                page.wait_for_timeout(3000)

        shot(page, "16-declaration-edi-x12-generated.jpg")

        browser.close()
    print("Patch complete.")


if __name__ == "__main__":
    run()
