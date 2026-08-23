import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def test_complete_browser_e2e():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("[E2E] 1. Opening Login page...")
        await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        title = await page.title()
        assert "SmartSalary" in title

        print("[E2E] 2. Logging in as employee@smartsalary.in...")
        await page.fill("#login-email", "employee@smartsalary.in")
        await page.fill("#login-password", "Password123!")
        await page.click("#btn-login")
        await page.wait_for_url("**/dashboard", timeout=6000)
        assert page.url.endswith("/dashboard")
        print("  -> Logged in successfully, landed on dashboard!")

        print("[E2E] 3. Navigating to Calculator...")
        await page.goto(f"{BASE_URL}/calculator", wait_until="networkidle")
        # Ensure authenticated navbar displays profile button
        profile_btn = page.locator("#profile-menu-btn")
        assert await profile_btn.is_visible()

        print("[E2E] 4. Performing Salary Calculation...")
        await page.click("#calculate-btn")
        await page.wait_for_timeout(1000)

        print("[E2E] 5. Signing out via Profile Menu...")
        await page.click("#profile-menu-btn")
        await page.wait_for_timeout(300)
        await page.click("#btn-logout")
        await page.wait_for_url(f"{BASE_URL}/", timeout=6000)
        assert page.url == f"{BASE_URL}/"
        print("  -> Logged out successfully!")

        print("[E2E] 6. Testing Forgot Password Modal...")
        await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        await page.click("button:has-text('Forgot password?')")
        await page.wait_for_timeout(300)
        await page.fill("#forgot-email", "employee@smartsalary.in")
        await page.click("#btn-forgot")
        await page.wait_for_timeout(1500)
        otp_screen = page.locator("#screen-otp")
        assert await otp_screen.is_visible()
        print("  -> OTP screen transitioned and displayed correctly!")

        await browser.close()
        assert len(console_errors) == 0, f"Encountered JS errors: {console_errors}"
        print("[E2E] COMPLETE SUCCESS: All browser workflows validated with ZERO console errors!")

if __name__ == "__main__":
    asyncio.run(test_complete_browser_e2e())
