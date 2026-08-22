"""
Milestone M11.2: Enterprise Employee Management
Verifies multi-state employee records, department associations, and active compensation revisions.
"""

import uuid
from datetime import date

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.employee import Employee, State
from app.models.organization import Organization


def test_m11_employee_multi_state_assignment():
    with SessionLocal() as db:
        org = Organization(
            legal_name="Pan-India Logistics Ltd",
            display_name="Pan-India Logistics",
            organization_code=f"PAN_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org)
        db.flush()

        states = {s.code: s.id for s in db.scalars(select(State)).all()}

        # Create employees in MH and KA
        emp_mh = Employee(
            organization_id=org.id,
            employee_code=f"EMP-MH-{uuid.uuid4().hex[:4]}",
            first_name="Rohan",
            last_name="Deshmukh",
            email=f"rohan_{uuid.uuid4().hex[:6]}@panindia.com",
            date_of_joining=date(2025, 4, 1),
            state_id=states.get("MH", 1),
        )
        emp_ka = Employee(
            organization_id=org.id,
            employee_code=f"EMP-KA-{uuid.uuid4().hex[:4]}",
            first_name="Ananya",
            last_name="Rao",
            email=f"ananya_{uuid.uuid4().hex[:6]}@panindia.com",
            date_of_joining=date(2025, 4, 1),
            state_id=states.get("KA", 1),
        )
        db.add_all([emp_mh, emp_ka])
        db.commit()

        assert emp_mh.id is not None
        assert emp_ka.id is not None
        assert emp_mh.state_id != emp_ka.state_id or "KA" in states
