"""Capture the extended screenshot set that shows off the AI features.

Output: project-audit/screenshots-v2/*.png (overwrites the previous v2 set).

This is the "AI showcase" capture, taking advantage of the bigger seeded
dataset (52 shipments, 27 voice amendments, 28 CoOs, $2.3M+ duty savings)
to surface every AI surface the UI offers:

  01 - Login (logged out)
  02 - Login (filled)
  03 - Dashboard (full-page, AI insights, action queue, sparklines)
  04 - Dashboard, scrolled (jurisdictions + modules)
  05 - Shipments list (52 rows, filter chips)
  06 - Shipments list filtered to blocked
  07 - Shipment detail (AI summary, voice cross-validation)
  08 - Shipment detail with cross-validation result rendered
  09 - Analytics (volume + savings area chart)
  10 - Analytics scrolled (FTA bars + pie + jurisdictions)
  11 - Command palette
  12 - Command palette filtered to "AI"
  13 - Mobile dashboard (375px)
  14 - Tablet dashboard (768px)
  15 - Mobile login
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
DEMO_EMAIL = "demo@tradepath.ai"
DEMO_PASS = "DemoPass1!"


def login(page, email: str = DEMO_EMAIL, password: str = DEMO_PASS) -> None:
    page.goto(f"{APP_URL}/login", wait_until="networkidle")
    page.fill('input[type="email"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard", timeout=10_000)
    time.sleep(0.5)


def shoot(page, name: str, *, full_page: bool = True) -> None:
    out = OUTPUT_DIR / f"{name}.png"
    page.screenshot(path=str(out), full_page=full_page)
    print(f"  captured {out.name}")


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        # ---- Desktop 1440 -------------------------------------------------
        desktop = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2.0,
        )
        page = desktop.new_page()

        # 01 — Login logged-out
        page.goto(f"{APP_URL}/login", wait_until="networkidle")
        time.sleep(0.8)
        shoot(page, "01-login", full_page=False)

        # 02 — Login filled (paused before submit)
        page.fill('input[type="email"]', DEMO_EMAIL)
        page.fill('input[type="password"]', DEMO_PASS)
        time.sleep(0.4)
        shoot(page, "02-login-filled", full_page=False)

        # Login proper
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard", timeout=10_000)
        time.sleep(5.0)  # AI insights stream finish

        # 03 — Dashboard top
        shoot(page, "02-dashboard", full_page=True)

        # 04 — Dashboard scrolled — scroll to mid + bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        time.sleep(0.6)
        shoot(page, "02b-dashboard-scrolled-mid", full_page=False)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.6)
        shoot(page, "02c-dashboard-scrolled-bottom", full_page=False)

        # 05 — Shipments list
        page.goto(f"{APP_URL}/shipments", wait_until="networkidle")
        time.sleep(1.5)
        shoot(page, "03-shipments", full_page=True)

        # 06 — Shipments filtered to blocked
        page.click("button:has-text('Blocked')")
        time.sleep(0.6)
        shoot(page, "03b-shipments-filtered-blocked", full_page=False)

        # 07 — Shipment detail
        # Reset filter first
        page.click("button:has-text('All')")
        time.sleep(0.4)
        # Click the first row that has a voice amendment indicator (we'll pick the first row).
        first_row = page.query_selector("table tbody tr")
        if first_row:
            first_row.click()
            page.wait_for_url("**/shipments/*", timeout=5_000)
            time.sleep(3.0)
            shoot(page, "05-shipment-detail", full_page=True)

            # 08 — Trigger cross-validation, capture mid-thinking
            page.click("button:has-text('Cross-validate')")
            time.sleep(0.8)  # capture the AI-thinking shimmer
            shoot(page, "05b-shipment-cross-validate-running", full_page=False)
            time.sleep(3.0)  # wait for completion
            shoot(page, "05c-shipment-cross-validate-done", full_page=True)

        # 09 — Analytics
        page.goto(f"{APP_URL}/analytics", wait_until="networkidle")
        time.sleep(2.5)
        shoot(page, "04-analytics", full_page=True)

        # 10 — Analytics scrolled
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.6)
        shoot(page, "04b-analytics-scrolled", full_page=False)

        # 11 — Command palette
        page.goto(f"{APP_URL}/dashboard", wait_until="networkidle")
        time.sleep(1.0)
        page.keyboard.press("Control+k")
        time.sleep(0.6)
        shoot(page, "06-command-palette", full_page=False)

        # 12 — Command palette filtered to AI commands
        page.keyboard.type("ai")
        time.sleep(0.5)
        shoot(page, "06b-command-palette-ai-filtered", full_page=False)
        page.keyboard.press("Escape")
        time.sleep(0.3)

        # 13 — Classification page (form + right-rail GRI rules)
        page.goto(f"{APP_URL}/classification", wait_until="networkidle")
        time.sleep(1.5)
        shoot(page, "08-classification", full_page=False)

        # 14 — Screening page
        page.goto(f"{APP_URL}/screening", wait_until="networkidle")
        time.sleep(1.5)
        shoot(page, "09-screening", full_page=False)

        # 15 — Documents page
        page.goto(f"{APP_URL}/documents", wait_until="networkidle")
        time.sleep(1.5)
        shoot(page, "10-documents", full_page=False)

        desktop.close()

        # ---- Tablet 768 ---------------------------------------------------
        tablet = browser.new_context(viewport={"width": 768, "height": 1024}, device_scale_factor=2.0)
        tp = tablet.new_page()
        login(tp)
        time.sleep(4.0)
        shoot(tp, "11-dashboard-tablet", full_page=True)
        tp.goto(f"{APP_URL}/shipments", wait_until="networkidle")
        time.sleep(1.5)
        shoot(tp, "11b-shipments-tablet", full_page=False)
        tablet.close()

        # ---- Mobile 390 ---------------------------------------------------
        mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2.0)
        mp = mobile.new_page()
        mp.goto(f"{APP_URL}/login", wait_until="networkidle")
        time.sleep(0.6)
        shoot(mp, "12-login-mobile", full_page=False)
        mp.fill('input[type="email"]', DEMO_EMAIL)
        mp.fill('input[type="password"]', DEMO_PASS)
        mp.click('button[type="submit"]')
        mp.wait_for_url("**/dashboard", timeout=10_000)
        time.sleep(4.0)
        shoot(mp, "07-dashboard-mobile", full_page=True)
        mp.goto(f"{APP_URL}/shipments", wait_until="networkidle")
        time.sleep(1.5)
        shoot(mp, "07b-shipments-mobile", full_page=False)
        mp.goto(f"{APP_URL}/analytics", wait_until="networkidle")
        time.sleep(2.0)
        shoot(mp, "07c-analytics-mobile", full_page=True)
        mobile.close()

        browser.close()
    print(f"\nDone. Output in {OUTPUT_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
