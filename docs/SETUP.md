# SmartSalary Development Setup

## Prerequisites
- Python 3.13.x
- PostgreSQL 16+ (Local service or Docker)
- Git

## Quickstart

### 1. Environment Configuration
Create a `.env` file in the project root:
```bash
cp .env.example .env
```

### 2. Virtual Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r backend/requirements-dev.txt
```

### 3. Database Migration
```bash
cd backend
alembic upgrade head
```

### 4. Seed Reference Data
```bash
python -m app.seeds.seed_reference_data
```

### 5. Start Application Server
```bash
uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000` to view the platform and architecture explorer.

## Running Tests & Linters
```bash
# Linting
ruff check backend/

# Test Suite
pytest -v backend/tests
```
