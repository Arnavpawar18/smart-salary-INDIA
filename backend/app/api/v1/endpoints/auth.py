from datetime import date
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_middleware import (
    CSRFProtection,
    clear_auth_cookies,
    get_current_user,
    set_auth_cookies,
)
from app.core.database import get_db
from app.core.security import JWTProvider, PasswordHasher
from app.models.auth import Role, User, user_roles
from app.models.employee import Employee
from app.repositories.session_repository import SessionRepository

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    phone: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.get("/csrf-token")
def get_csrf_token(response: Response):
    """Provides a fresh signed CSRF token."""
    token = CSRFProtection.generate_csrf_token()
    response.set_cookie(key="csrf_token", value=token, httponly=False, samesite="lax", path="/")
    return {"csrf_token": token}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    req: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Registers a new employee user account and establishes a persistent refresh session."""
    existing = db.scalar(select(User).where(User.email == req.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password with Argon2id
    hashed = PasswordHasher.hash_password(req.password)
    user = User(
        email=req.email,
        hashed_password=hashed,
        full_name=req.full_name,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    # Assign default EMPLOYEE role
    emp_role = db.scalar(select(Role).where(Role.name == "EMPLOYEE"))
    if emp_role:
        db.execute(user_roles.insert().values(user_id=user.id, role_id=emp_role.id))

    # Create associated Employee record
    employee_code = f"EMP-{user.id:04d}"
    employee = Employee(
        user_id=user.id,
        employee_code=employee_code,
        first_name=req.full_name.split()[0] if req.full_name else "User",
        last_name=req.full_name.split()[-1] if len(req.full_name.split()) > 1 else "",
        email=req.email,
        phone_number=req.phone,
        date_of_joining=date.today(),
        state_id=1,  # Default KA
    )
    db.add(employee)
    db.commit()
    db.refresh(user)

    # Issue JWT tokens and create persistent session
    access_token = JWTProvider.create_access_token(user_id=user.id, role="EMPLOYEE", employee_id=employee.id)
    raw_refresh, jti, expire = JWTProvider.create_refresh_token(user_id=user.id)

    session_repo = SessionRepository(db)
    session_repo.create_session(
        user_id=user.id,
        raw_refresh_token=raw_refresh,
        jti=jti,
        expires_at=expire,
    )

    csrf_token = CSRFProtection.generate_csrf_token()
    set_auth_cookies(response, access_token=access_token, raw_refresh_token=raw_refresh, csrf_token=csrf_token)

    return {
        "message": "Account created successfully",
        "user": {"id": user.id, "email": user.email, "role": "EMPLOYEE", "employee_id": employee.id},
        "csrf_token": csrf_token,
    }


@router.post("/login")
def login_user(
    req: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticates user with Argon2id and establishes a persistent refresh session."""
    user = db.scalar(select(User).where(User.email == req.email))
    if not user or not PasswordHasher.verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Resolve primary role and employee_id
    role_stmt = select(Role.name).join(user_roles, Role.id == user_roles.c.role_id).where(user_roles.c.user_id == user.id)
    role_name = db.scalar(role_stmt) or "EMPLOYEE"
    emp = db.scalar(select(Employee).where(Employee.user_id == user.id))
    employee_id = emp.id if emp else None

    # Issue tokens
    access_token = JWTProvider.create_access_token(user_id=user.id, role=role_name, employee_id=employee_id)
    raw_refresh, jti, expire = JWTProvider.create_refresh_token(user_id=user.id)

    session_repo = SessionRepository(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    session_repo.create_session(
        user_id=user.id,
        raw_refresh_token=raw_refresh,
        jti=jti,
        expires_at=expire,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    csrf_token = CSRFProtection.generate_csrf_token()
    set_auth_cookies(response, access_token=access_token, raw_refresh_token=raw_refresh, csrf_token=csrf_token)

    return {
        "message": "Login successful",
        "user": {"id": user.id, "email": user.email, "role": role_name, "employee_id": employee_id},
        "csrf_token": csrf_token,
    }


@router.post("/refresh")
def refresh_session(
    response: Response,
    request: Request,
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
):
    """Rotates refresh token and returns fresh access token with reuse detection."""
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        payload = JWTProvider.decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload["sub"])
        old_jti = payload["jti"]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {e}") from e

    session_repo = SessionRepository(db)
    new_raw_refresh, new_jti, new_expire = JWTProvider.create_refresh_token(user_id=user_id)

    try:
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        session_repo.rotate_session(
            old_jti=old_jti,
            new_raw_refresh_token=new_raw_refresh,
            new_jti=new_jti,
            new_expires_at=new_expire,
            ip_address=client_ip,
            user_agent=user_agent,
        )
    except ValueError as e:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail=str(e)) from e

    # Fetch user role & employee
    role_stmt = select(Role.name).join(user_roles, Role.id == user_roles.c.role_id).where(user_roles.c.user_id == user_id)
    role_name = db.scalar(role_stmt) or "EMPLOYEE"
    emp = db.scalar(select(Employee).where(Employee.user_id == user_id))
    employee_id = emp.id if emp else None

    access_token = JWTProvider.create_access_token(user_id=user_id, role=role_name, employee_id=employee_id)
    set_auth_cookies(response, access_token=access_token, raw_refresh_token=new_raw_refresh)

    return {"message": "Session refreshed successfully"}


@router.post("/logout")
def logout_user(
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
):
    """Revokes active refresh session and clears auth cookies."""
    if refresh_token:
        try:
            payload = JWTProvider.decode_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                session_repo = SessionRepository(db)
                session_repo.revoke_session(jti)
        except Exception:
            pass

    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_authenticated_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns profile for currently authenticated user."""
    role_stmt = select(Role.name).join(user_roles, Role.id == user_roles.c.role_id).where(user_roles.c.user_id == current_user.id)
    role_name = db.scalar(role_stmt) or "EMPLOYEE"
    emp = db.scalar(select(Employee).where(Employee.user_id == current_user.id))

    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": role_name,
        "employee_id": emp.id if emp else None,
        "employee_details": {
            "first_name": emp.first_name if emp else "",
            "last_name": emp.last_name if emp else "",
            "work_email": emp.email if emp else "",
            "phone": emp.phone_number if emp else None,
        } if emp else None,
    }
