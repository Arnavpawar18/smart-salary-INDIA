import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.core.security import PasswordHasher
from app.models.auth import User

db = SessionLocal()
try:
    users = db.query(User).all()
    print(f"Total Users in DB: {len(users)}")
    for u in users:
        print(f"User: id={u.id}, email={u.email}, is_active={u.is_active}")
        if u.email == "employee@smartsalary.in":
            matches = PasswordHasher.verify_password("Password123!", u.hashed_password)
            print(f"  Password123! matches: {matches}")
finally:
    db.close()
