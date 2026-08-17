# SmartSalary India 🇮🇳

**SmartSalary** is a **Python-First Full-Stack Financial Intelligence Platform** engineered for Indian statutory salary, income tax (Old & New Regimes), Provident Fund (EPF/EPS/EDLI), and State Professional Tax compliance.

---

## 🏛️ Phase 1 Platform Architecture

- **Full-Stack Presentation**: FastAPI + Jinja2 + HTMX + Tailwind CSS.
- **Data & Models**: SQLAlchemy 2.x Declarative Models, PostgreSQL 16+, Alembic migrations.
- **Frozen Domain Model**: Exactly 40 domain tables + 1 `alembic_version` = 41 PostgreSQL tables.
- **Financial Boundary**: Pure, deterministic, zero-I/O financial engine boundary in `app/engine/` (calculation algorithms integrated in Phase 2).

---

## 🚀 Quickstart

```bash
# 1. Setup Virtualenv & Dependencies
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements-dev.txt

# 2. Run Database Migrations (40 domain tables)
cd backend
alembic upgrade head

# 3. Seed Reference Data (Roles, 36 States/UTs, Tax Periods, Rule Shells)
python -m app.seeds.seed_reference_data

# 4. Start Development Server
uvicorn app.main:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🧪 Testing & Code Quality

```bash
# Linting & Formatting Check
ruff check backend/

# Pytest Suite (Schema integrity, migration lifecycle, seed idempotency, web pages)
pytest -v backend/tests
```

---

## 📜 Documentation

- [System Architecture](docs/ARCHITECTURE.md)
- [Authoritative 40-Table Domain Schema](docs/DOMAIN_SCHEMA.md)
- [Development Setup Guide](docs/SETUP.md)
