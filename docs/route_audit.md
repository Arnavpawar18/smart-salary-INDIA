# SmartSalary India — Dead-Link & Route Audit (Phase 2 Master)

| UI Link / Action | Source File | Target Path / Endpoint | Method | Auth Required | Role Required | Route Status | Notes |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Navbar Brand** | `navbar.html` | `/` | GET | No | Any | ✓ LIVE | Renders Homepage |
| **Salary Calculator** | `navbar.html` | `/calculator` | GET | No | Any | ✓ LIVE | Renders Calculator |
| **Payroll Dashboard** | `navbar.html` | `/dashboard` | GET | Yes | Employee | ✓ LIVE | Renders Employee Dashboard |
| **Payslips Portal** | `navbar.html` | `/payslips` | GET | Yes | Employee | ✓ LIVE | Renders Payslips Portal |
| **Evidence & Status** | `navbar.html` | `/system-status` | GET | No | Any | ✓ LIVE | Renders Regulatory Sources & Status |
| **Sign In** | `navbar.html` | `/login` | GET | No | Any | ✓ LIVE | Renders Auth Portal in Login Mode |
| **Register** | `navbar.html` | `/register` | GET | No | Any | ✓ LIVE | Renders Auth Portal in Register Mode |
| **Sign Out** | `navbar.html` | `/api/v1/auth/logout` | POST | Yes | Any | ✓ LIVE | Clears cookies & session |
| **AI Explains Trigger** | `navbar.html` | `toggleAiDrawer()` | JS | Optional | Any | ✓ LIVE | Opens AI Drawer |
| **Calculate HTMX** | `calculator.html` | `/calculator/calculate` | POST | Optional | Any | ✓ LIVE | Returns Result Partial |
| **How was this calculated?** | `result_minimal.html` | `/calculator/{id}/how` | GET | No | Any | ✓ LIVE | Returns Trace & Ledger Partial |
| **Print Summary Export** | `how_details.html` | `/calculator/export/{id}` | GET | No | Any | ✓ LIVE | Renders printable salary sheet |
| **What-if Simulator** | `how_details.html` | `/calculator/what-if` | POST | No | Any | ✓ LIVE | Returns raise simulator partial |
| **Company Dashboard Link** | `home.html` | `/dashboard` | GET | Yes | Organization Admin | ❌ MISROUTED | Routes to personal dashboard instead of enterprise portal |
| **Enterprise Dashboard API** | Backend API | `/api/v1/enterprise/dashboard-summary` | GET | Yes | Org Admin / HR | ✓ LIVE | Scoped to TenantContext |
| **Enterprise Employees API** | Backend API | `/api/v1/enterprise/employees` | GET | Yes | Org Admin / HR | ✓ LIVE | Scoped to TenantContext |
| **Payslip Upload API** | `payslips.html` | `/api/v1/payslips/upload` | POST | Yes | Employee | ✓ LIVE | Document extraction & recon |
