from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.models.auth import Role, User, role_permissions
from app.models.organization import Organization, OrganizationMembership


@dataclass
class TenantContext:
    """
    Authoritative Context for the authenticated user within an enterprise organization.
    Enforces defense-in-depth tenant isolation across all enterprise services and queries.
    """

    organization_id: int
    user_id: int
    membership_id: int
    role_name: str
    permission_names: set[str]
    organization: Organization


def get_tenant_context(
    current_user: User = Depends(get_current_user),
    x_organization_id: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> TenantContext:
    """
    Resolves and verifies the authenticated user's organization membership.
    CRITICAL SECURITY MANDATE: Never trust an arbitrary organization_id without verified membership.
    """
    # 1. Fetch all active memberships for this user
    stmt = (
        select(OrganizationMembership, Organization, Role)
        .join(Organization, OrganizationMembership.organization_id == Organization.id)
        .join(Role, OrganizationMembership.role_id == Role.id)
        .where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.status == "ACTIVE",
            Organization.status.in_(["ACTIVE", "PENDING_SETUP"]),
        )
    )
    memberships = list(db.execute(stmt).all())

    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an active membership in any organization.",
        )

    # 2. Match requested organization or default to first primary membership
    target_membership = None
    if x_organization_id:
        try:
            target_org_id = int(x_organization_id)
            for mem, org, role in memberships:
                if org.id == target_org_id:
                    target_membership = (mem, org, role)
                    break
            if not target_membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: user is not an active member of the requested organization.",
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Organization-Id header format"
            ) from e
    else:
        target_membership = memberships[0]

    mem, org, role = target_membership

    # 3. Resolve permissions for role
    perm_stmt = select(role_permissions.c.permission_id).where(role_permissions.c.role_id == role.id)
    # We fetch permission names or IDs
    perm_ids = {str(pid) for pid in db.scalars(perm_stmt).all()}

    return TenantContext(
        organization_id=org.id,
        user_id=current_user.id,
        membership_id=mem.id,
        role_name=role.name,
        permission_names=perm_ids,
        organization=org,
    )
