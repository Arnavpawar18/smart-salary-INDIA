import asyncio
import json

from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def run_full_browser_e2e():
    report = {
        "summary": {},
        "pages": {},
        "workflows": {},
        "defects": [],
        "network_log": [],
        "console_errors": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 768}, accept_downloads=True)
        page = await context.new_page()

        page.on("console", lambda msg: report["console_errors"].append(f"[{msg.type.upper()}] {msg.text}") if msg.type in ["error", "warning"] else None)
        page.on("requestfailed", lambda req: report["network_log"].append(f"FAIL {req.method} {req.url} -> {req.failure}"))

        def handle_response(res):
            if res.status >= 400:
                report["network_log"].append(f"HTTP_{res.status} {res.request.method} {res.url}")
        page.on("response", handle_response)

        print("\n==================================================")
        print("1. AUDITING HOME & NAVBAR")
        print("==================================================")
        resp = await page.goto(f"{BASE_URL}/", wait_until="networkidle")
        title = await page.title()
        print(f"GET / -> Status: {resp.status}, Title: {title}")
        report["pages"]["home"] = {"status": resp.status, "title": title}

        # Check hero title visibility
        hero_text = await page.locator("h1").first.inner_text()
        print(f"Hero Header: {hero_text.strip()}")

        # Navbar items
        nav_routes = [
            ("/", "Home"),
            ("/calculator", "Salary Calculator"),
            ("/dashboard", "Payroll Dashboard"),
            ("/tax-center", "Tax Center"),
            ("/payslips", "Payslips"),
            ("/evidence", "Evidence & Status"),
            ("/help", "Help Center"),
            ("/enterprise", "Company / Enterprise"),
            ("/security", "Security Center")
        ]

        for path, name in nav_routes:
            r = await page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
            t = await page.title()
            print(f"Navbar -> {name} ({path}): HTTP {r.status} | Title: {t}")
            report["pages"][name] = {"path": path, "status": r.status, "title": t}

        print("\n==================================================")
        print("2. CALCULATOR REAL USER FLOW & DATA TRACE")
        print("==================================================")
        await page.goto(f"{BASE_URL}/calculator", wait_until="networkidle")

        # Select state KA, FY 2025-26, New Regime, monthly gross 1,00,000 (Annual 12,00,000)
        await page.select_option("#financial_year", "2025-26")
        await page.select_option("#state_code", "KA")
        await page.check("input[name='regime'][value='NEW']")
        await page.fill("#salary-input", "100000")

        # Listen for calculate request and response
        async with page.expect_response(lambda r: "/calculator/calculate" in r.url or "/api/v1/calculations" in r.url) as response_info:
            await page.click("button[type='submit']")
        calc_res = await response_info.value
        print(f"Calculation trigger -> HTTP {calc_res.status}")

        await page.wait_for_timeout(1000)

        # Inspect DOM output in calculation result container
        calc_html = await page.inner_html("#calculation-result-container")
        print("Calculator DOM rendered successfully:", len(calc_html) > 100)
        report["workflows"]["calculator_ka_new_12L"] = {
            "status": calc_res.status,
            "dom_rendered": len(calc_html) > 100
        }

        print("\n==================================================")
        print("3. PRINT / PDF / JSON / COPY ACTIONS")
        print("==================================================")
        await page.goto(f"{BASE_URL}/print-summary", wait_until="networkidle")
        print(f"GET /print-summary -> HTTP {page.url}")

        # Test download PDF if available
        # Test export JSON
        export_buttons = await page.locator("button, a").all()
        print(f"Found {len(export_buttons)} interactive elements on print summary page.")

        print("\n==================================================")
        print("4. TAX CENTER CONTEXT & VALUE AUDIT")
        print("==================================================")
        tc_res = await page.goto(f"{BASE_URL}/tax-center", wait_until="networkidle")
        print(f"GET /tax-center -> HTTP {tc_res.status}")
        tc_body = await page.inner_text("body")
        print("Tax Center text length:", len(tc_body))

        print("\n==================================================")
        print("5. AI CHATBOT INQUIRE AUDIT")
        print("==================================================")
        # Try triggering AI drawer or testing chat endpoint
        chat_res = await page.request.post(
            f"{BASE_URL}/api/v1/chat/inquire",
            data=json.dumps({"question": "Why is my income tax this amount?", "salary_context": {"annual_gross": 1200000, "regime": "NEW", "tax": 0}}),
            headers={"Content-Type": "application/json"}
        )
        print(f"POST /api/v1/chat/inquire -> HTTP {chat_res.status}")
        if chat_res.status == 200:
            print("Chat response snippet:", (await chat_res.json()).get("response", "")[:120])

        print("\n==================================================")
        print("6. ENTERPRISE SUITE AUDIT")
        print("==================================================")
        enterprise_pages = [
            "/enterprise",
            "/enterprise/risk-engine",
            "/enterprise/tax-analytics",
            "/enterprise/compliance-reports",
            "/enterprise/approvals",
            "/enterprise/audit-logs"
        ]
        for ep in enterprise_pages:
            eresp = await page.goto(f"{BASE_URL}{ep}", wait_until="networkidle")
            print(f"Enterprise {ep} -> HTTP {eresp.status}")
            report["pages"][f"enterprise_{ep}"] = eresp.status

        print("\n==================================================")
        print("7. PAYSLIPS AUDIT")
        print("==================================================")
        ps_res = await page.goto(f"{BASE_URL}/payslips", wait_until="networkidle")
        print(f"GET /payslips -> HTTP {ps_res.status}")

        print("\n==================================================")
        print("8. RESPONSIVE VIEWPORT CHECKS")
        print("==================================================")
        viewports = [(390, 844), (768, 1024), (1366, 768), (1920, 1080)]
        for w, h in viewports:
            await page.set_viewport_size({"width": w, "height": h})
            await page.goto(f"{BASE_URL}/calculator", wait_until="networkidle")
            # Check horizontal overflow
            scroll_width = await page.evaluate("document.documentElement.scrollWidth")
            client_width = await page.evaluate("document.documentElement.clientWidth")
            has_overflow = scroll_width > client_width
            print(f"Viewport {w}x{h} -> scrollWidth={scroll_width}, clientWidth={client_width}, Overflow={has_overflow}")

        await browser.close()

    print("\n==================================================")
    print("AUDIT EXECUTION SUMMARY")
    print(f"Console errors/warnings: {len(report['console_errors'])}")
    for ce in report["console_errors"][:10]:
        print("  -", ce)
    print(f"Network errors: {len(report['network_log'])}")
    for ne in report["network_log"][:10]:
        print("  -", ne)

if __name__ == "__main__":
    asyncio.run(run_full_browser_e2e())
