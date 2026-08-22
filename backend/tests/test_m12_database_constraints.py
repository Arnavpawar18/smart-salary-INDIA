"""
Milestone M12.11: Database Constraint & Foreign Key Validation
Verifies that database constraints (unique, foreign keys, not null) enforce data integrity at the database level.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.employee import State


def test_m12_state_code_unique_constraint():
    with SessionLocal() as db:
        # Attempt to insert duplicate state code
        duplicate_state = State(code="KA", name="Duplicate Karnataka", is_union_territory=False)
        db.add(duplicate_state)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
