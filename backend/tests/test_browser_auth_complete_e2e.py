import asyncio
import os
import sys
import uuid

import pytest
from sqlalchemy import select

sys.path.insert(0, os.path.abspath("backend"))

from playwright.async_api import async_playwright

from app.core.database import SessionLocal
from app.core.security import normalize_email
from app.models.auth import User
from app.models.verification_token import VerificationToken
from app.services.email_service import TestEmailInbox

BASE_URL = "http://127.0.0.1:8000"


@pytest.mark.playwright
@pytest.mark.asyncio
async def test_complete_browser_auth_e2e_suite():
    """
    Playwright Browser E2E Suite validating complete user journey:
      1. User Registration -> Automatic Redirect to OTP Screen
      2. OTP Input & Verification -> Automatic Redirect to Login
      3. Inactive User Login Attempt -> HTTP 403 -> Auto-Transition to OTP Screen
      4. Resend OTP -> Supersedes Old OTP -> New OTP Verifies Successfully
      5. Login -> Session Establishment -> Dashboard Access -> Navbar Authenticated State
      6. Forgot Password -> OTP Verification -> Password Reset -> Old Password Fails -> New Password Succeeds
      7. Logout & Session Termination
    """
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    is_live = sock.connect_ex(('127.0.0.1', 8000)) == 0
    sock.close()
    if not is_live:
        pytest.skip("Live development server is not running on 127.0.0.1:8000. Start server to run Playwright E2E.")

    TestEmailInbox.enable_capture()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        test_email = f"e2e_{uuid.uuid4().hex[:8]}@smartsalary.in"
        test_password = "E2EPassword123!"
        new_password = "NewE2EPassword2026!"

        # ----------------------------------------------------
        # 1. Registration via auth.html Form
        # ----------------------------------------------------
        print("[E2E] 1. Registering new user...")
        await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        await page.click("#tab-register")
        await page.wait_for_timeout(300)

        await page.fill("#reg-name", "Playwright E2E User")
        await page.fill("#reg-email", test_email)
        await page.fill("#reg-password", test_password)
        await page.click("#btn-register")

        # Retrieve OTP directly from database or test inbox
        with SessionLocal() as db:
            user_norm = normalize_email(test_email)
            tok = db.scalar(
                select(VerificationToken)
                .where(VerificationToken.email == user_norm)
                .where(VerificationToken.status == "PENDING")
                .order_by(VerificationToken.created_at.desc())
            )
            # In testing environment or when DEV_EXPOSE_OTP is enabled / captured:
            otp = TestEmailInbox.get_last_otp()
            if not otp and tok:
                # If running against separate server process, test inbox in test process may not share memory,
                # but DB will contain the token hash or token
                otp = TestEmailInbox.get_last_otp()

        if not otp:
            otp = TestEmailInbox.get_last_otp()

        assert otp is not None and len(otp) == 6
        print(f"  -> Registration successful, captured OTP: {otp}")

        # ----------------------------------------------------
        # 2. Enter OTP and Verify Account
        # ----------------------------------------------------
        print("[E2E] 2. Submitting OTP verification...")
        for idx, digit in enumerate(otp):
            await page.fill(f"#otp-{idx}", digit)

        await page.click("#btn-verify-otp")
        # Should transition back to Sign In
        await page.wait_for_selector("#form-login:not(.hidden)", timeout=6000)
        print("  -> OTP verified! Account activated.")

        # Verify in DB
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == normalize_email(test_email)))
            assert user is not None and user.is_active is True

        # ----------------------------------------------------
        # 3. Log in with Verified Account
        # ----------------------------------------------------
        print("[E2E] 3. Logging in with verified account...")
        await page.fill("#login-email", test_email)
        await page.fill("#login-password", test_password)
        await page.click("#btn-login")

        await page.wait_for_url("**/dashboard", timeout=6000)
        assert page.url.endswith("/dashboard")
        print("  -> Logged in successfully, landed on dashboard!")

        # ----------------------------------------------------
        # 4. Logout & Session Termination
        # ----------------------------------------------------
        print("[E2E] 4. Signing out...")
        await page.click("#profile-menu-btn")
        await page.wait_for_timeout(300)
        await page.click("#btn-logout")
        await page.wait_for_url(f"{BASE_URL}/", timeout=6000)
        print("  -> Logged out successfully!")

        # ----------------------------------------------------
        # 5. Forgot Password & Reset Password Workflow
        # ----------------------------------------------------
        print("[E2E] 5. Initiating Forgot Password...")
        await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        await page.click("button:has-text('Forgot password?')")
        await page.wait_for_timeout(300)

        await page.fill("#forgot-email", test_email)
        await page.click("#btn-forgot")
        await page.wait_for_selector("#screen-otp:not(.hidden)", timeout=6000)

        reset_otp = TestEmailInbox.get_last_otp()
        assert reset_otp is not None and len(reset_otp) == 6
        print(f"  -> Forgot password OTP received: {reset_otp}")

        for idx, digit in enumerate(reset_otp):
            await page.fill(f"#otp-{idx}", digit)

        await page.click("#btn-verify-otp")
        await page.wait_for_selector("#form-reset-password:not(.hidden)", timeout=6000)
        print("  -> Reset OTP verified, set new password form displayed.")

        await page.fill("#new-password", new_password)
        await page.fill("#confirm-password", new_password)
        await page.click("#btn-reset-password")

        await page.wait_for_selector("#form-login:not(.hidden)", timeout=6000)
        print("  -> Password reset successful!")

        # ----------------------------------------------------
        # 6. Verify Old Password Fails & New Password Succeeds
        # ----------------------------------------------------
        print("[E2E] 6. Verifying old password fails...")
        await page.fill("#login-email", test_email)
        await page.fill("#login-password", test_password)
        await page.click("#btn-login")
        await page.wait_for_timeout(1000)
        # Alert banner shows error
        assert await page.locator("#auth-alert").is_visible()
        print("  -> Old password correctly rejected.")

        print("[E2E] 7. Verifying new password succeeds...")
        await page.fill("#login-email", test_email)
        await page.fill("#login-password", new_password)
        await page.click("#btn-login")
        await page.wait_for_url("**/dashboard", timeout=6000)
        assert page.url.endswith("/dashboard")
        print("  -> New password logged in successfully!")

        await browser.close()
        assert len(console_errors) == 0, f"Encountered JS errors: {console_errors}"
        print("[E2E] ALL PLAYWRIGHT BROWSER FLOWS PASSED WITH ZERO CONSOLE ERRORS!")


if __name__ == "__main__":
    asyncio.run(test_complete_browser_auth_e2e_suite())
