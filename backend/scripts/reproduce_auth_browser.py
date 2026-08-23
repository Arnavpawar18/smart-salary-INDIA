import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def test_auth_browser_flows():
    results = {
        "login": {},
        "forgot_password": {},
        "network_traffic": [],
        "console_logs": [],
        "errors": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        page.on("console", lambda msg: results["console_logs"].append(f"[{msg.type.upper()}] {msg.text}"))
        page.on("requestfailed", lambda req: results["network_traffic"].append(f"REQ_FAILED: {req.method} {req.url} -> {req.failure}"))

        async def on_response(res):
            if "auth" in res.url or res.status >= 400:
                try:
                    body = await res.text()
                except Exception:
                    body = "<binary>"
                results["network_traffic"].append({
                    "url": res.url,
                    "method": res.request.method,
                    "status": res.status,
                    "response_body": body[:300]
                })
        page.on("response", on_response)

        print("\n--- Testing Login Flow in Browser ---")
        await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        await page.fill("#login-email", "employee@smartsalary.in")
        await page.fill("#login-password", "Password123!")

        # Click Sign In and wait
        await page.click("#btn-login")
        await page.wait_for_timeout(2000)

        current_url = page.url
        print(f"Post-login URL: {current_url}")
        results["login"]["final_url"] = current_url

        alert_text = ""
        try:
            alert_el = page.locator("#auth-alert")
            if await alert_el.is_visible():
                alert_text = (await alert_el.inner_text()).strip()
        except Exception as e:
            alert_text = f"Error reading alert: {e}"
        print(f"Login Alert text: {alert_text}")
        results["login"]["alert_text"] = alert_text

        print("\n--- Testing Forgot Password Flow in Browser ---")
        await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        # Click Forgot Password link
        await page.click("button:has-text('Forgot password?')")
        await page.wait_for_timeout(500)

        await page.fill("#forgot-email", "employee@smartsalary.in")
        await page.click("#btn-forgot")
        await page.wait_for_timeout(2000)

        fp_alert_text = ""
        try:
            alert_el = page.locator("#auth-alert")
            if await alert_el.is_visible():
                fp_alert_text = (await alert_el.inner_text()).strip()
        except Exception as e:
            fp_alert_text = f"Error reading alert: {e}"
        print(f"Forgot Password Alert text: {fp_alert_text}")
        results["forgot_password"]["alert_text"] = fp_alert_text

        # Check OTP screen visibility
        otp_screen_visible = await page.locator("#screen-otp").is_visible()
        print(f"OTP Screen visible: {otp_screen_visible}")
        results["forgot_password"]["otp_screen_visible"] = otp_screen_visible

        await browser.close()

    print("\n--- Network Traffic Summary ---")
    for net in results["network_traffic"]:
        print(net)

    print("\n--- Console Logs ---")
    for log in results["console_logs"]:
        print(log)

if __name__ == "__main__":
    asyncio.run(test_auth_browser_flows())
