.PHONY: help install migrate seed run test lint format clean

help:
	@echo "SmartSalary Development Commands"
	@echo "================================"
	@echo "make install    Install backend dependencies"
	@echo "make migrate    Run Alembic migrations to head"
	@echo "make seed       Seed reference and structural data"
	@echo "make run        Start FastAPI server with live reload"
	@echo "make test       Run complete Pytest suite"
	@echo "make lint       Run Ruff linter"
	@echo "make format     Run Ruff formatter"
	@echo "make clean      Remove caches and build artifacts"

install:
	pip install -r backend/requirements-dev.txt

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m app.seeds.seed_reference_data

run:
	cd backend && uvicorn app.main:app --reload --port 8000

test:
	pytest -v backend/tests

lint:
	ruff check backend/

format:
	ruff format backend/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
