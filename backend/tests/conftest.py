import os
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.base import Base
from app.seeds.seed_reference_data import seed_reference_data

TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL_TEST",
    "postgresql+psycopg://postgres:postgres@localhost:5433/smartsalary_test",
)

assert "test" in TEST_DATABASE_URL.lower(), "TEST SAFETY VIOLATION: Test database URL must contain 'test'!"


@pytest.fixture(scope="session")
def engine():
    try:
        test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 2})
        with test_engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
    except Exception:
        test_engine = create_engine("sqlite:///:memory:", echo=False)

    Base.metadata.create_all(bind=test_engine)

    with Session(bind=test_engine) as seed_session:
        seed_reference_data(seed_session)

    yield test_engine

    try:
        with test_engine.connect() as conn:
            conn.execute(sa.text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
            conn.commit()
    except Exception:
        Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def reset_in_memory_rate_limiters():
    from app.core.rate_limiter import InMemoryRateLimiter

    InMemoryRateLimiter.clear()
