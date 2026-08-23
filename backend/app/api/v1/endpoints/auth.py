import logging
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.auth_middleware import (
    CSRFProtection,
    clear_auth_cookies,
    get_current_user,
    set_auth_cookies,
    verify_csrf,
)
from app.core.database import get_db
from app.core.rate_limiter import InMemoryRateLimiter
from app.core.security import JWTProvider, PasswordHasher, normalize_email
from app.models.auth import Role, User, user_roles
from app.models.employee import Employee, State
from app.models.session import UserSession
from app.models.verification_token import VerificationToken
from app.repositories.session_repository import SessionRepository
from app.services.audit_service import AuditEvent, AuditService
from app.services.email_service import EmailService
from app.services.otp_service import OTPPurpose, OTPService

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    phone: str | None = None
    sector: str | None = Field(default="IT / Software")
    occupation: str | None = Field(default="SOFTWARE_IT")
    state_code: str | None = Field(default="KA")
    employment_type: str | None = Field(default="FULL_TIME")
    guest_session_token: str | None = None


class VerifyEmailOtpRequest(BaseModel):
    verification_id: uuid.UUID
    otp: str = Field(min_length=6, max_length=6)


class ResendOtpRequest(BaseModel):
    verification_id: uuid.UUID


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyPasswordResetOtpRequest(BaseModel):
    verification_id: uuid.UUID
    otp: str = Field(min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8)
    confirm_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
    confirm_password: str


@router.get("/csrf-token")
def get_csrf_token(response: Response):
    """Provides a fresh signed CSRF token."""
    token = CSRFProtection.generate_csrf_token()
    response.set_cookie(key="csrf_token", value=token, httponly=False, samesite="lax", path="/")
    return {"csrf_token": token}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    req: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Registers a new employee user account in an unverified state (is_active=False),
    creates the verification token, and dispatches a 6-digit email OTP.
    Zero JWT tokens or cookies are issued at this stage.
    """
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    InMemoryRateLimiter.check_rate_limit(f"register:{client_ip}", max_requests=10, window_seconds=60)

    normalized_email = normalize_email(req.email)
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing and existing.is_active:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password with Argon2id
    hashed = PasswordHasher.hash_password(req.password)

    if existing and not existing.is_active:
        # Re-registration of an unverified account: update password and profile
        user = existing
        user.hashed_password = hashed
        user.full_name = req.full_name
        db.flush()
    else:
        user = User(
            email=normalized_email,
            hashed_password=hashed,
            full_name=req.full_name,
            is_active=False,  # Gated until email OTP verification
            is_superuser=False,
        )
        db.add(user)
        db.flush()

        # Assign default EMPLOYEE role
        emp_role = db.scalar(select(Role).where(Role.name == "EMPLOYEE"))
        if emp_role:
            db.execute(user_roles.insert().values(user_id=user.id, role_id=emp_role.id))

    # Create/update associated Employee record
    employee_code = f"EMP-{user.id:04d}"
    state_id = 1
    if req.state_code:
        state_obj = db.scalar(select(State).where(State.code == req.state_code.strip().upper()))
        if state_obj:
            state_id = state_obj.id

    employee = db.scalar(select(Employee).where(Employee.user_id == user.id))
    if not employee:
        employee = Employee(
            user_id=user.id,
            employee_code=employee_code,
            first_name=req.full_name.split()[0] if req.full_name else "User",
            last_name=req.full_name.split()[-1] if len(req.full_name.split()) > 1 else "",
            email=normalized_email,
            phone_number=req.phone,
            date_of_joining=date.today(),
            employment_type=req.employment_type or "FULL_TIME",
            state_id=state_id,
        )
        db.add(employee)
    else:
        employee.first_name = req.full_name.split()[0] if req.full_name else "User"
        employee.last_name = req.full_name.split()[-1] if len(req.full_name.split()) > 1 else ""
        employee.phone_number = req.phone
        employee.employment_type = req.employment_type or "FULL_TIME"
        employee.state_id = state_id

    db.commit()
    db.refresh(user)

    # Create EMAIL_VERIFICATION token & send email
    token, raw_otp = OTPService.create_verification_token(
        db=db,
        email=normalized_email,
        purpose=OTPPurpose.EMAIL_VERIFICATION,
        user_id=user.id,
    )

    # Dispatch verification OTP synchronously and ensure delivery
    if not EmailService.send_email_verification_otp(to_email=normalized_email, otp=raw_otp):
        raise HTTPException(status_code=502, detail="Failed to send verification email")

    return {
        "status": "OTP_REQUIRED",
        "message": "Account created. A 6-digit verification code has been sent to your email.",
        "verification_id": str(token.verification_id),
        "email": normalized_email,
    }


@router.post("/verify-email-otp")
def verify_email_otp(
    req: VerifyEmailOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Verifies the email verification OTP, activates user account (is_active=True).
    User can now proceed to login.
    """
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    InMemoryRateLimiter.check_rate_limit(f"verify_otp:{client_ip}", max_requests=20, window_seconds=60)

    success, msg, token = OTPService.verify_otp(
        db=db,
        verification_id=req.verification_id,
        raw_otp=req.otp,
        expected_purpose=OTPPurpose.EMAIL_VERIFICATION,
    )

    if not success or not token:
        raise HTTPException(status_code=400, detail=msg)

    # Activate user
    user = None
    if token.user_id:
        user = db.scalar(select(User).where(User.id == token.user_id))
    if not user:
        user = db.scalar(select(User).where(User.email == normalize_email(token.email)))

    if not user:
        raise HTTPException(status_code=404, detail="User account associated with this verification code not found.")

    user.is_active = True
    db.commit()
    db.refresh(user)

    AuditService.log_event(
        db=db,
        action=AuditEvent.EMAIL_VERIFICATION_SUCCESS,
        entity_name="USER",
        user_id=user.id,
        entity_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {
        "status": "VERIFIED",
        "message": "Email verified successfully. You can now log in to your account.",
    }


@router.post("/resend-otp")
def resend_otp(
    req: ResendOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Resends a fresh OTP for an existing verification record with 60-second cooldown enforcement.
    """
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    InMemoryRateLimiter.check_rate_limit(f"resend_otp:{client_ip}", max_requests=10, window_seconds=60)

    old_token = db.scalar(
        select(VerificationToken).where(VerificationToken.verification_id == req.verification_id)
    )
    if not old_token:
        raise HTTPException(status_code=404, detail="Verification session not found.")

    new_token, raw_otp = OTPService.create_verification_token(
        db=db,
        email=old_token.email,
        purpose=old_token.purpose,
        user_id=old_token.user_id,
    )

    if old_token.purpose == OTPPurpose.EMAIL_VERIFICATION:
        if not EmailService.send_email_verification_otp(to_email=old_token.email, otp=raw_otp):
            raise HTTPException(status_code=502, detail="Failed to resend verification email")
    else:
        if not EmailService.send_password_reset_otp(to_email=old_token.email, otp=raw_otp):
            raise HTTPException(status_code=502, detail="Failed to resend password reset email")

    return {
        "status": "RESENT",
        "message": "A new verification code has been dispatched to your email.",
        "verification_id": str(new_token.verification_id),
    }


@router.post("/forgot-password")
def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Initiates two-stage password reset with anti-enumeration protection.
    Always returns a generic success response.
    """
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    InMemoryRateLimiter.check_rate_limit(f"forgot_pwd:{client_ip}", max_requests=5, window_seconds=60)

    normalized_email = normalize_email(req.email)
    user = db.scalar(select(User).where(User.email == normalized_email))

    if not user:
        return {
            "status": "NOT_FOUND",
            "message": "No account found with this email address. Please check your spelling or register a new account.",
            "verification_id": None,
        }

    if not user.is_active:
        # Create email verification token if account was never activated
        token, raw_otp = OTPService.create_verification_token(
            db=db,
            email=normalized_email,
            purpose=OTPPurpose.EMAIL_VERIFICATION,
            user_id=user.id,
        )
        EmailService.send_email_verification_otp(to_email=normalized_email, otp=raw_otp)
        return {
            "status": "INACTIVE",
            "message": "Your account is pending email verification. A new activation code has been sent to your email.",
            "verification_id": str(token.verification_id),
            "purpose": "EMAIL_VERIFICATION",
        }

    token, raw_otp = OTPService.create_verification_token(
        db=db,
        email=normalized_email,
        purpose=OTPPurpose.PASSWORD_RESET,
        user_id=user.id,
    )
    if not EmailService.send_password_reset_otp(to_email=normalized_email, otp=raw_otp):
        raise HTTPException(status_code=502, detail="Failed to send password reset email. Please try again.")

    AuditService.log_event(
        db=db,
        action=AuditEvent.PASSWORD_RESET_REQUESTED,
        entity_name="USER",
        user_id=user.id,
        entity_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {
        "status": "SUCCESS",
        "message": f"A 6-digit password reset code has been sent to {normalized_email}.",
        "verification_id": str(token.verification_id),
        "purpose": "PASSWORD_RESET",
    }


@router.post("/verify-password-reset-otp")
def verify_password_reset_otp(
    req: VerifyPasswordResetOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Stage 1 of Password Reset: Validates 6-digit OTP and issues a short-lived signed reset_token (JWT).
    """
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    InMemoryRateLimiter.check_rate_limit(f"verify_reset_otp:{client_ip}", max_requests=20, window_seconds=60)

    success, msg, token = OTPService.verify_otp(
        db=db,
        verification_id=req.verification_id,
        raw_otp=req.otp,
        expected_purpose=OTPPurpose.PASSWORD_RESET,
    )

    if not success or not token:
        raise HTTPException(status_code=400, detail=msg)

    user = None
    if token.user_id:
        user = db.scalar(select(User).where(User.id == token.user_id))
    if not user:
        user = db.scalar(select(User).where(User.email == normalize_email(token.email)))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    reset_token = JWTProvider.create_password_reset_token(user_id=user.id, email=user.email)

    return {
        "status": "OTP_VERIFIED",
        "message": "Identity verified. You may now set a new password.",
        "reset_token": reset_token,
    }


@router.post("/reset-password")
def reset_password(
    req: ResetPasswordRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Stage 2 of Password Reset: Consumes signed reset_token, updates password with Argon2id,
    and revokes all active user sessions for zero-trust security.
    """
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    InMemoryRateLimiter.check_rate_limit(f"reset_pwd:{client_ip}", max_requests=5, window_seconds=60)

    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirmation do not match")

    try:
        payload = JWTProvider.decode_token(req.reset_token)
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid token type for password reset")
        user_id = int(payload["sub"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid or expired reset token: {e}") from e

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")

    # Hash new password with Argon2id
    user.hashed_password = PasswordHasher.hash_password(req.new_password)
    db.commit()

    # Revoke ALL existing active sessions
    session_repo = SessionRepository(db)
    session_repo.revoke_all_user_sessions(user.id)
    clear_auth_cookies(response)

    AuditService.log_event(
        db=db,
        action=AuditEvent.PASSWORD_CHANGED,
        entity_name="USER",
        user_id=user.id,
        entity_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {
        "status": "PASSWORD_RESET_SUCCESS",
        "message": "Password has been reset successfully. Please log in with your new password.",
    }


@router.post("/login")
def login_user(
    req: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticates user with Argon2id and establishes a persistent refresh session."""
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    InMemoryRateLimiter.check_rate_limit(f"login:{client_ip}", max_requests=15, window_seconds=60)

    normalized_email = normalize_email(req.email)
    user = db.scalar(select(User).where(User.email == normalized_email))
    if not user or not PasswordHasher.verify_password(req.password, user.hashed_password):
        AuditService.log_event(
            db=db,
            action=AuditEvent.LOGIN_FAILURE,
            entity_name="USER",
            user_id=user.id if user else None,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_active:
        # Find latest active token or issue a fresh one
        token = OTPService.get_latest_active_token(db=db, email=normalized_email, purpose=OTPPurpose.EMAIL_VERIFICATION)
        if not token:
            try:
                token, raw_otp = OTPService.create_verification_token(
                    db=db,
                    email=normalized_email,
                    purpose=OTPPurpose.EMAIL_VERIFICATION,
                    user_id=user.id,
                )
                EmailService.send_email_verification_otp(to_email=normalized_email, otp=raw_otp)
            except Exception as e:
                logger.warning("Failed to auto-issue fresh OTP during inactive login for %s: %s", normalized_email, e)

        v_id = str(token.verification_id) if token else str(uuid.uuid4())
        raise HTTPException(
            status_code=403,
            detail={
                "code": "EMAIL_NOT_VERIFIED",
                "verification_id": v_id,
                "email": normalized_email,
                "message": "Email not verified. Please enter the verification code sent to your email.",
            },
        )

    # Resolve primary role and employee_id
    role_stmt = (
        select(Role.name).join(user_roles, Role.id == user_roles.c.role_id).where(user_roles.c.user_id == user.id)
    )
    role_name = db.scalar(role_stmt) or "EMPLOYEE"
    emp = db.scalar(select(Employee).where(Employee.user_id == user.id))
    employee_id = emp.id if emp else None

    # Issue tokens
    raw_refresh, jti, expire = JWTProvider.create_refresh_token(user_id=user.id)
    access_token = JWTProvider.create_access_token(
        user_id=user.id, role=role_name, employee_id=employee_id, session_jti=jti
    )

    session_repo = SessionRepository(db)
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

    AuditService.log_event(
        db=db,
        action=AuditEvent.LOGIN_SUCCESS,
        entity_name="USER",
        user_id=user.id,
        entity_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

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
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    InMemoryRateLimiter.check_rate_limit(f"refresh:{client_ip}", max_requests=30, window_seconds=60)

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
        active_session = session_repo.get_active_session_by_jti(old_jti)
        if not active_session:
            raise ValueError("Session is expired or revoked")
        if active_session.token_hash != JWTProvider.compute_token_hash(refresh_token):
            session_repo.revoke_all_user_sessions(user_id)
            raise ValueError("Refresh token hash mismatch. All user sessions have been terminated for security.")
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
        AuditService.log_event(
            db=db,
            action=AuditEvent.REFRESH_REUSE_DETECTED,
            entity_name="USER",
            user_id=user_id,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        raise HTTPException(status_code=401, detail=str(e)) from e

    # Fetch user role & employee
    role_stmt = (
        select(Role.name).join(user_roles, Role.id == user_roles.c.role_id).where(user_roles.c.user_id == user_id)
    )
    role_name = db.scalar(role_stmt) or "EMPLOYEE"
    emp = db.scalar(select(Employee).where(Employee.user_id == user_id))
    employee_id = emp.id if emp else None

    access_token = JWTProvider.create_access_token(
        user_id=user_id, role=role_name, employee_id=employee_id, session_jti=new_jti
    )
    set_auth_cookies(response, access_token=access_token, raw_refresh_token=new_raw_refresh)

    return {"message": "Session refreshed successfully"}


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    response: Response,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Changes password and revokes all active refresh sessions for security.
    """
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    InMemoryRateLimiter.check_rate_limit(f"pwd_change:{client_ip}", max_requests=5, window_seconds=60)

    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirmation do not match")

    if not PasswordHasher.verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    # Update password
    current_user.hashed_password = PasswordHasher.hash_password(req.new_password)
    db.commit()

    # Revoke all existing sessions
    session_repo = SessionRepository(db)
    session_repo.revoke_all_user_sessions(current_user.id)

    # Issue a fresh single session
    raw_refresh, jti, expire = JWTProvider.create_refresh_token(user_id=current_user.id)
    session_repo.create_session(
        user_id=current_user.id,
        raw_refresh_token=raw_refresh,
        jti=jti,
        expires_at=expire,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    role_stmt = (
        select(Role.name)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id == current_user.id)
    )
    role_name = db.scalar(role_stmt) or "EMPLOYEE"
    emp = db.scalar(select(Employee).where(Employee.user_id == current_user.id))
    employee_id = emp.id if emp else None

    access_token = JWTProvider.create_access_token(
        user_id=current_user.id, role=role_name, employee_id=employee_id, session_jti=jti
    )
    set_auth_cookies(response, access_token=access_token, raw_refresh_token=raw_refresh)

    AuditService.log_event(
        db=db,
        action=AuditEvent.PASSWORD_CHANGED,
        entity_name="USER",
        user_id=current_user.id,
        entity_id=current_user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {"message": "Password changed successfully. All previous sessions revoked."}


@router.get("/sessions")
def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists active sessions for the authenticated user."""
    session_repo = SessionRepository(db)
    sessions = session_repo.get_user_active_sessions(current_user.id)
    return [
        {
            "id": s.id,
            "jti": str(s.jti),
            "issued_at": s.issued_at.isoformat(),
            "last_used_at": s.last_used_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "ip_address": s.ip_address or "127.0.0.1",
            "user_agent": s.user_agent or "Browser Session",
        }
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
def revoke_individual_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revokes a specific session belonging strictly to the authenticated user."""
    session = db.scalar(select(UserSession).where(UserSession.id == session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: cannot revoke another user's session")

    session_repo = SessionRepository(db)
    session_repo.revoke_session(str(session.jti))

    AuditService.log_event(
        db=db,
        action=AuditEvent.SESSION_REVOKED,
        entity_name="USER",
        user_id=current_user.id,
        entity_id=session.id,
    )
    return {"message": "Session revoked successfully"}


@router.post("/logout-all")
def logout_all_sessions(
    response: Response,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revokes ALL active sessions for the user and clears cookies."""
    session_repo = SessionRepository(db)
    count = session_repo.revoke_all_user_sessions(current_user.id)
    clear_auth_cookies(response)

    AuditService.log_event(
        db=db,
        action=AuditEvent.LOGOUT_ALL,
        entity_name="USER",
        user_id=current_user.id,
        entity_id=current_user.id,
    )
    return {"message": f"All {count} active sessions revoked successfully"}


@router.post("/logout")
def logout_user(
    response: Response,
    _: None = Depends(verify_csrf),
    access_token: Annotated[str | None, Cookie()] = None,
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
):
    """Revokes active refresh/access session and clears auth cookies."""
    session_repo = SessionRepository(db)
    if refresh_token:
        try:
            payload = JWTProvider.decode_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                session_repo.revoke_session(jti)
        except Exception:
            pass

    if access_token:
        try:
            payload = JWTProvider.decode_token(access_token)
            session_jti = payload.get("session_jti")
            if session_jti:
                session_repo.revoke_session(session_jti)
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
    role_stmt = (
        select(Role.name)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id == current_user.id)
    )
    role_name = db.scalar(role_stmt) or "EMPLOYEE"
    emp = db.scalar(select(Employee).where(Employee.user_id == current_user.id))

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": role_name,
        "employee_id": emp.id if emp else None,
        "employee_details": {
            "first_name": emp.first_name if emp else "",
            "last_name": emp.last_name if emp else "",
            "work_email": emp.email if emp else "",
            "phone": emp.phone_number if emp else None,
        }
        if emp
        else None,
    }
