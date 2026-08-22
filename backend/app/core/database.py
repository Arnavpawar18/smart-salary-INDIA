import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Bind engine - check if Postgres is connectable, otherwise SQLite memory fallback
DATABASE_URL = os.environ.get("DATABASE_URL", settings.DATABASE_URL)


def _init_engine():
    if "psycopg" in DATABASE_URL or "postgresql" in DATABASE_URL:
        try:
            eng = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                connect_args={"connect_timeout": 1},
            )
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return eng
        except Exception:
            pass
    from sqlalchemy.pool import StaticPool

    from app.models.base import Base

    sqlite_eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=sqlite_eng)

    # Auto-seed reference data for in-memory SQLite instances
    from app.seeds.seed_reference_data import seed_reference_data

    with Session(bind=sqlite_eng) as seed_session:
        seed_reference_data(seed_session)

    return sqlite_eng


engine = _init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Dynamically checks PostgreSQL connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False
