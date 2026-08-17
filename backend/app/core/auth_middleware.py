import hmac
import os
import secrets
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import JWTProvider
from app.models.auth import Permission, Role, User, role_permissions, user_roles

CSRF_SECRET = os.environ.get("CSRF_SECRET", "smartsalary-csrf-secret-change-in-production-2026")
IS_PRODUCTION = os.environ.get("ENVIRONMENT", "development").lower() == "production"


class CSRFProtection:
    """Signed double-submit CSRF token generator and validator."""

    @classmethod
    def generate_csrf_token(cls) -> str:
        random_bytes = secrets.token_hex(16)
        signature = hmac.new(CSRF_SECRET.encode("utf-8"), random_bytes.encode("utf-8"), "sha256").hexdigest()
        return f"{random_bytes}.{signature}"

    @classmethod
    def validate_csrf_token(cls, token: str) -> bool:
        if not token or "." not in token:
            return False
        parts = token.split(".")
        if len(parts) != 2:
            return False
        random_bytes, sig = parts
        expected_sig = hmac.new(CSRF_SECRET.encode("utf-8"), random_bytes.encode("utf-8"), "sha256").hexdigest()
        return hmac.compare_digest(sig, expected_sig)


def set_auth_cookies(
    response: Response,
    access_token: str,
    raw_refresh_token: str,
    csrf_token: str | None = None,
) -> None:
    """Sets HTTP-only Secure SameSite cookies for authentication."""
    # Access token cookie (15 mins)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=15 * 60,
        path="/",
    )
    # Refresh token cookie (7 days)
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/api/v1/auth/refresh",
    )
    # Non-HttpOnly CSRF token cookie for frontend forms/HTMX
    if csrf_token:
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,
            secure=IS_PRODUCTION,
            samesite="lax",
            max_age=7 * 24 * 60 * 60,
            path="/",
        )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
    response.delete_cookie("csrf_token", path="/")


async def verify_csrf(
    request: Request,
    x_csrf_token: Annotated[str | None, Header()] = None,
):
    """Dependency verifying CSRF for mutating requests."""
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        token = x_csrf_token
        if not token:
            form_data = await request.form()
            token = form_data.get("csrf_token")

        if not token or not CSRFProtection.validate_csrf_token(str(token)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF verification failed or missing token",
            )


def get_current_user(
    request: Request,
    access_token: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    """Extracts and verifies authenticated User from HTTP-only cookie or Bearer header."""
    token = access_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = JWTProvider.decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = int(payload["sub"])
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Authentication failed: {e}") from e

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account disabled or not found")

    return user


def require_permission(required_permission_code: str):
    """RBAC Dependency: checks that authenticated user possesses the specific permission."""

    def permission_dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        stmt = (
            select(Permission.code)
            .join(role_permissions, Permission.id == role_permissions.c.permission_id)
            .join(Role, Role.id == role_permissions.c.role_id)
            .join(user_roles, Role.id == user_roles.c.role_id)
            .where(user_roles.c.user_id == current_user.id)
        )
        user_permissions = set(db.scalars(stmt).all())

        if required_permission_code not in user_permissions and "admin.full_access" not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: '{required_permission_code}'",
            )
        return current_user

    return permission_dependency
