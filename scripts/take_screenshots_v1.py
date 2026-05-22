#!/usr/bin/env python3
"""TradePath AI — post-redesign Playwright screenshot suite.

Covers: login, dashboard, shipments, classification, screening (ShipmentSelector open),
declarations, COO, FTA, documents, analytics, and the ShipmentSelector combobox.
"""
import asyncio, os
import httpx
from playwright.async_api import async_playwright

BASE_URL  = "http://localhost:5007"
API_BASE  = "http://127.0.0.1:8037/api/v1"
OUT_DIR   = os.path.join(os.path.dirname(__file__), "screenshots")

EMAIL    = "screenshot_final@tradepath.ai"
PASSWORD = "ScreenPass1!"

EXPAND_CSS = """
  * { animation-duration: 0ms !important; transition-duration: 0ms !important; }
  .animate-spin { animation: none !important; }
"""

os.makedirs(OUT_DIR, exist_ok=True)

counter = [0]

def api_register_and_login() -> str:
    with httpx.Client(timeout=15) as client:
        client.post(f"{API_BASE}/auth/register", json={
            "email": EMAIL, "password": PASSWORD,
            "full_name": "Screenshot User", "role": "customs_broker",
        })
        resp = client.post(
            f"{API_BASE}/auth/login",
            data={"username": EMAIL, "password": PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


def seed_shipment(token: str) -> dict:
    with httpx.Client(timeout=15, headers={"Authorization": f"Bearer {token}"}) as client:
        r = client.post(f"{API_BASE}/shipments", json={
            "origin_country": "US", "destination_country": "DE",
            "transport_mode": "sea", "incoterms": "CIF",
            "exporter_name": "Acme Corp", "importer_name": "Euro GmbH",
            "total_value_usd": 50000, "total_weight_kg": 1200,
        })
        r.raise_for_status()
        return r.json()


async def inject_auth(page, token: str):
    await page.evaluate(f"localStorage.setItem('token', '{token}')")


async def shot(page, label: str, full_page: bool = True):
    counter[0] += 1
    name = f"{counter[0]:02d}-{label}.png"
    path = os.path.join(OUT_DIR, name)
    await page.screenshot(path=path, full_page=full_page, timeout=60_000)
    print(f"  [screenshot] {name}")
    return name


async def w(page, ms: int = 2000):
    await page.wait_for_timeout(ms)


async def goto(page, path: str, token: str):
    await page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
    await inject_auth(page, token)
    await w(page, 2500)


async def open_shipment_selector(page, ship_ref: str, label: str, token: str) -> bool:
    """Try to open ShipmentSelector, screenshot it open, then select ship_ref. Returns True on success."""
    try:
        btn = page.locator("button").filter(has_text="Select a shipment")
        if await btn.count() == 0:
            # Maybe already selected
            return False
        await btn.first.click()
        await w(page, 1000)
        await shot(page, f"{label}-shipment-selector-open")
        # Select the seeded shipment by ref
        item = page.locator(f"text={ship_ref}").first
        if await item.count() > 0:
            await item.click()
            await w(page, 600)
        else:
            # Close dropdown with Escape
            await page.keyboard.press("Escape")
            await w(page, 400)
        return True
    except Exception as e:
        print(f"  [warn] ShipmentSelector on {label}: {e}")
        try:
            await page.keyboard.press("Escape")
            await w(page, 400)
        except Exception:
            pass
        return False


async def main():
    token = api_register_and_login()
    print(f"  [auth] JWT obtained for {EMAIL}")

    shipment = seed_shipment(token)
    ship_id  = shipment["id"]
    ship_ref = shipment.get("reference_number", ship_id)
    print(f"  [seed] shipment created: {ship_ref} ({ship_id})")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()

        # Inject CSS to disable animations
        await page.add_style_tag(content=EXPAND_CSS)

        # ── 01 Login page ─────────────────────────────────────────────────────
        await page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
        await w(page, 2000)
        await shot(page, "login-page")

        # ── 02 Login form filled ──────────────────────────────────────────────
        await page.fill('input[type="email"]', EMAIL)
        await page.fill('input[type="password"]', PASSWORD)
        await shot(page, "login-form-filled")

        # ── 03 Submit login → dashboard ───────────────────────────────────────
        await page.click('button[type="submit"]')
        try:
            await page.wait_for_url("**/dashboard", timeout=12_000)
        except Exception:
            pass
        await w(page, 3000)
        await inject_auth(page, token)
        await shot(page, "dashboard-after-login")

        # ── 04 Dashboard full ─────────────────────────────────────────────────
        await goto(page, "/dashboard", token)
        await shot(page, "dashboard-full")

        # ── 05 Shipments list ─────────────────────────────────────────────────
        await goto(page, "/shipments", token)
        await shot(page, "shipments-list")

        # ── 06 Shipment detail ────────────────────────────────────────────────
        await goto(page, f"/shipments/{ship_id}", token)
        await shot(page, "shipment-detail")

        # ── 07 Classification page ────────────────────────────────────────────
        await goto(page, "/classification", token)
        await shot(page, "classification-page")

        # Fill classification form if there's a textarea
        try:
            ta = page.locator("textarea").first
            if await ta.count() > 0:
                await ta.fill("Industrial hydraulic pump for manufacturing")
                await w(page, 500)
        except Exception:
            pass
        await shot(page, "classification-form-filled")

        # ── 09 Screening page ─────────────────────────────────────────────────
        await goto(page, "/screening", token)
        await shot(page, "screening-page")

        # Open ShipmentSelector — screenshot open dropdown
        await open_shipment_selector(page, ship_ref, "screening", token)
        # Fill party name
        try:
            party_inputs = page.locator('input[placeholder*="party"], input[placeholder*="Party"], input[placeholder*="name"], input[placeholder*="Name"]')
            if await party_inputs.count() > 0:
                await party_inputs.first.fill("Acme Trading LLC")
                await w(page, 400)
        except Exception:
            pass
        await shot(page, "screening-form-with-shipment-selector")

        # ── Declarations page ─────────────────────────────────────────────────
        await goto(page, "/declarations", token)
        await shot(page, "declarations-page")
        await open_shipment_selector(page, ship_ref, "declarations", token)
        await shot(page, "declarations-form-with-shipment")

        # ── COO page ──────────────────────────────────────────────────────────
        await goto(page, "/coo", token)
        await shot(page, "coo-page")
        await open_shipment_selector(page, ship_ref, "coo", token)
        await shot(page, "coo-form-with-shipment")

        # ── FTA page ──────────────────────────────────────────────────────────
        await goto(page, "/fta", token)
        await shot(page, "fta-page")
        await open_shipment_selector(page, ship_ref, "fta", token)
        await shot(page, "fta-form-with-shipment")

        # ── Documents page ────────────────────────────────────────────────────
        await goto(page, "/documents", token)
        await shot(page, "documents-page")

        # ── Analytics page ────────────────────────────────────────────────────
        await goto(page, "/analytics", token)
        await w(page, 1500)
        await shot(page, "analytics-page")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await w(page, 1000)
        await shot(page, "analytics-scrolled")

        # ── Sidebar / navigation ──────────────────────────────────────────────
        await goto(page, "/dashboard", token)
        await shot(page, "sidebar-navigation")

        # ── Mobile viewport ───────────────────────────────────────────────────
        mobile_ctx = await browser.new_context(viewport={"width": 375, "height": 812})
        mpage = await mobile_ctx.new_page()
        await mpage.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
        await mpage.wait_for_timeout(2000)
        await mpage.fill('input[type="email"]', EMAIL)
        await mpage.fill('input[type="password"]', PASSWORD)
        await mpage.click('button[type="submit"]')
        try:
            await mpage.wait_for_url("**/dashboard", timeout=12_000)
        except Exception:
            pass
        await mpage.wait_for_timeout(3000)
        await inject_auth(mpage, token)
        await mpage.screenshot(path=os.path.join(OUT_DIR, f"{counter[0]+1:02d}-dashboard-mobile-375.png"), full_page=True, timeout=60_000)
        counter[0] += 1
        print(f"  [screenshot] {counter[0]:02d}-dashboard-mobile-375.png")

        await mpage.goto(f"{BASE_URL}/shipments", wait_until="domcontentloaded")
        await inject_auth(mpage, token)
        await mpage.wait_for_timeout(2500)
        await mpage.screenshot(path=os.path.join(OUT_DIR, f"{counter[0]+1:02d}-shipments-mobile-375.png"), full_page=True, timeout=60_000)
        counter[0] += 1
        print(f"  [screenshot] {counter[0]:02d}-shipments-mobile-375.png")
        await mobile_ctx.close()

        await browser.close()

    files = sorted(os.listdir(OUT_DIR))
    print(f"\n  Done — {len(files)} screenshots in {OUT_DIR}")
    for f in files:
        print(f"    {f}")


if __name__ == "__main__":
    asyncio.run(main())
