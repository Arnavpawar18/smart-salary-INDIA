import sys
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import engine as app_engine


def test_alembic_migration_lifecycle(tmp_path):
    """
    Test complete Alembic migration cycle:
    1. Downgrade base -> 0 domain tables exist
    2. Upgrade head -> domain tables exist
    """
    ini_path = str(BACKEND_DIR / "alembic.ini")
    alembic_cfg = Config(ini_path)
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    if "postgresql" in str(app_engine.url) or "psycopg" in str(app_engine.url):
        db_url = settings.DATABASE_URL
    else:
        test_db_file = tmp_path / "test_alembic.db"
        db_url = f"sqlite:///{test_db_file}"

    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    engine = create_engine(db_url)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(engine)
    tables_restored = set(inspector.get_table_names())
    domain_tables_restored = {t for t in tables_restored if t != "alembic_version"}
    assert len(domain_tables_restored) >= 40, (
        f"Expected domain tables after upgrade, found {len(domain_tables_restored)}"
    )
    assert "user_sessions" in domain_tables_restored
    assert "organizations" in domain_tables_restored
    assert "payroll_runs" in domain_tables_restored
    assert "tax_declarations" in domain_tables_restored

    # 2. Downgrade to base
    command.downgrade(alembic_cfg, "base")
    inspector = inspect(engine)
    tables_after_downgrade = set(inspector.get_table_names())
    domain_tables_downgrade = {t for t in tables_after_downgrade if t != "alembic_version"}
    assert len(domain_tables_downgrade) == 0, (
        f"Expected 0 domain tables after downgrade, found {len(domain_tables_downgrade)}"
    )

    # 3. Upgrade back to head to leave clean state
    command.upgrade(alembic_cfg, "head")

    engine.dispose()
