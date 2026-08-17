import sys
from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import engine


def test_alembic_migration_lifecycle():
    """
    Test complete Alembic migration cycle:
    1. Upgrade head -> 40 domain tables exist
    2. Downgrade base -> 0 domain tables exist
    3. Upgrade head -> 40 domain tables restored cleanly
    """
    ini_path = str(BACKEND_DIR / "alembic.ini")
    alembic_cfg = Config(ini_path)
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(engine)
    tables_after_upgrade = set(inspector.get_table_names())
    # Exclude alembic metadata table
    domain_tables = {t for t in tables_after_upgrade if t != "alembic_version"}
    assert len(domain_tables) == 40, f"Expected 40 domain tables after upgrade, found {len(domain_tables)}"

    # 2. Downgrade to base
    command.downgrade(alembic_cfg, "base")
    inspector = inspect(engine)
    tables_after_downgrade = set(inspector.get_table_names())
    domain_tables_downgrade = {t for t in tables_after_downgrade if t != "alembic_version"}
    assert len(domain_tables_downgrade) == 0, f"Expected 0 domain tables after downgrade, found {len(domain_tables_downgrade)}"

    # 3. Upgrade back to head
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(engine)
    tables_restored = set(inspector.get_table_names())
    domain_tables_restored = {t for t in tables_restored if t != "alembic_version"}
    assert len(domain_tables_restored) == 40, f"Expected 40 domain tables after re-upgrade, found {len(domain_tables_restored)}"
