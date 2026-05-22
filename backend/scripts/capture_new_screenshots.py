"""Capture screenshots of the redesigned TradePath AI UI.

Reuses the playwright bundled with the backend venv so we don't depend on
node tooling. Each screen waits for the AI insights to stop streaming so
the captured frame shows finished content.

Usage::

    python -m scripts.capture_new_screenshots
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT / "project-audit" / "screenshots-v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

APP_URL = "http://localhost:5007"

SCREENS = [
    ("01-login", "/login", None, 0.4),
    ("02-dashboard", "/dashboard", "demo", 4.0),
    ("03-shipments", "/shipments", "demo", 2.0),
    ("04-analytics", "/analytics", "demo", 3.5),
    ("05-shipment-detail", "/shipments/{first_id}", "demo", 4.0),
]


def login(page, email: str, password: str) -> None:
    page.goto(f"{APP_URL}/login", wait_until="networkidle")
    page.fill('input[type="email"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard", timeout=10_000)


def get_first_shipment_id(page) -> str | None:
    page.goto(f"{APP_URL}/shipments", wait_until="networkidle")
    # Wait for the table to load — pick up the first row's reference monospace cell.
    page.wait_for_selector("table tbody tr", timeout=5_000)
    first = page.query_selector("table tbody tr")
    if not first:
        return None
    # Click the row → URL becomes /shipments/<uuid>
    first.click()
    page.wait_for_url("**/shipments/*", timeout=5_000)
    url = page.url
    return url.rsplit("/", 1)[-1]


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2.0,
        )
        page = context.new_page()

        # 01 — Login (logged out)
        page.goto(f"{APP_URL}/login", wait_until="networkidle")
        time.sleep(0.6)
        page.screenshot(path=str(OUTPUT_DIR / "01-login.png"), full_page=False)
        print("captured 01-login.png")

        # Login as demo
        login(page, "demo@tradepath.ai", "DemoPass1!")
        time.sleep(0.4)

        # 02 — Dashboard. Wait for AI insights to finish streaming.
        page.goto(f"{APP_URL}/dashboard", wait_until="networkidle")
        time.sleep(5.0)  # streamed text + sparklines
        page.screenshot(path=str(OUTPUT_DIR / "02-dashboard.png"), full_page=True)
        print("captured 02-dashboard.png")

        # 03 — Shipments table
        page.goto(f"{APP_URL}/shipments", wait_until="networkidle")
        time.sleep(1.5)
        page.screenshot(path=str(OUTPUT_DIR / "03-shipments.png"), full_page=True)
        print("captured 03-shipments.png")

        # 04 — Analytics
        page.goto(f"{APP_URL}/analytics", wait_until="networkidle")
        time.sleep(2.5)
        page.screenshot(path=str(OUTPUT_DIR / "04-analytics.png"), full_page=True)
        print("captured 04-analytics.png")

        # 05 — Shipment detail (first row)
        page.goto(f"{APP_URL}/shipments", wait_until="networkidle")
        page.wait_for_selector("table tbody tr", timeout=5_000)
        first = page.query_selector("table tbody tr")
        if first:
            first.click()
            page.wait_for_url("**/shipments/*", timeout=5_000)
            time.sleep(2.5)
            page.screenshot(path=str(OUTPUT_DIR / "05-shipment-detail.png"), full_page=True)
            print("captured 05-shipment-detail.png")

        # 06 — Cmd+K command palette
        page.goto(f"{APP_URL}/dashboard", wait_until="networkidle")
        time.sleep(0.5)
        page.keyboard.press("Control+k")
        time.sleep(0.6)
        page.screenshot(path=str(OUTPUT_DIR / "06-command-palette.png"), full_page=False)
        print("captured 06-command-palette.png")

        # 07 — Mobile dashboard (iPhone 14 width)
        mobile_ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2.0)
        mp = mobile_ctx.new_page()
        # Reuse the token by setting it in localStorage on first /login load.
        mp.goto(f"{APP_URL}/login", wait_until="networkidle")
        mp.fill('input[type="email"]', "demo@tradepath.ai")
        mp.fill('input[type="password"]', "DemoPass1!")
        mp.click('button[type="submit"]')
        mp.wait_for_url("**/dashboard", timeout=10_000)
        time.sleep(4.0)
        mp.screenshot(path=str(OUTPUT_DIR / "07-dashboard-mobile.png"), full_page=True)
        print("captured 07-dashboard-mobile.png")

        browser.close()
    print(f"\nAll screenshots saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
