from datetime import UTC, datetime
import re
from collections.abc import Mapping

from fastapi import HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy import Select, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.admin_audit.service import record_admin_audit_log
from app.domains.admin_auth.models import AdminAccount
from app.domains.admin_workspaces.schemas import WorkspaceCreateInput
from app.domains.memberships.models import MembershipRole
from app.domains.memberships.service import get_membership_by_tenant_and_user
from app.domains.memberships.service import create_membership
from app.domains.organizations.models import Organization
from app.domains.tenants.models import Tenant


def slugify_workspace_name(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if not base:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace name must include letters or numbers")
    return base[:120].strip("-")


def build_workspace_slug_query(candidate: str) -> Select[tuple[Tenant]]:
    return select(Tenant).where(or_(Tenant.slug == candidate, Tenant.subdomain == candidate))


def build_workspace_by_id_query(workspace_id: int) -> Select[tuple[Tenant]]:
    return select(Tenant).where(Tenant.id == workspace_id)


def get_workspace_by_id(session: Session, workspace_id: int) -> Tenant | None:
    return session.execute(build_workspace_by_id_query(workspace_id)).scalar_one_or_none()


def workspace_slug_exists(session: Session, candidate: str) -> bool:
    return session.execute(build_workspace_slug_query(candidate)).scalar_one_or_none() is not None


def allocate_workspace_slug(session: Session, name: str) -> str:
    base = slugify_workspace_name(name)
    candidate = base
    suffix = 2
    while workspace_slug_exists(session, candidate):
        suffix_text = f"-{suffix}"
        candidate = f"{base[: max(1, 120 - len(suffix_text))]}{suffix_text}"
        suffix += 1
    return candidate


def ensure_admin_can_create_workspace(admin_account: AdminAccount) -> None:
    if not admin_account.is_active or not admin_account.user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is inactive")


def build_workspace_creation_detail(
    *,
    actor_user_id: int,
    workspace_name: str,
    workspace_id: int | None = None,
    workspace_slug: str | None = None,
    reason: str | None = None,
) -> Mapping[str, object]:
    detail: dict[str, object] = {
        "actor_user_id": actor_user_id,
        "workspace_name": workspace_name,
    }
    if workspace_id is not None:
        detail["workspace_id"] = workspace_id
    if workspace_slug is not None:
        detail["workspace_slug"] = workspace_slug
    if reason is not None:
        detail["reason"] = reason
    return detail


def create_workspace_as_admin(
    session: Session,
    admin_account: AdminAccount,
    payload: WorkspaceCreateInput | dict[str, object],
    request: Request | None = None,
) -> Tenant:
    ensure_admin_can_create_workspace(admin_account)
    try:
        workspace_input = payload if isinstance(payload, WorkspaceCreateInput) else WorkspaceCreateInput.model_validate(payload)
    except ValidationError as exc:
        error_message = exc.errors()[0]["msg"] if exc.errors() else "Invalid workspace input"
        record_admin_audit_log(
            session,
            action="workspace_creation_failed",
            status="failed",
            request=request,
            admin_account_id=admin_account.id,
            target_type="workspace",
            target_id=None,
            detail=build_workspace_creation_detail(
                actor_user_id=admin_account.user_id,
                workspace_name=str(payload.get("name", "")) if isinstance(payload, dict) else "",
                reason=f"validation_error:{error_message}",
            ),
        )
        session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message) from exc

    record_admin_audit_log(
        session,
        action="workspace_creation_started",
        status="started",
        request=request,
        admin_account_id=admin_account.id,
        target_type="workspace",
        target_id=None,
        detail=build_workspace_creation_detail(
            actor_user_id=admin_account.user_id,
            workspace_name=workspace_input.name,
        ),
    )
    session.commit()

    try:
        with session.begin():
            slug = allocate_workspace_slug(session, workspace_input.name)
            tenant = Tenant(
                name=workspace_input.name,
                slug=slug,
                subdomain=slug,
                status="active",
            )
            session.add(tenant)
            session.flush()

            organization = Organization(tenant_id=tenant.id, name=workspace_input.name)
            session.add(organization)

            membership = get_membership_by_tenant_and_user(session, tenant.id, admin_account.user_id)
            if membership is None:
                create_membership(session, tenant.id, admin_account.user, MembershipRole.admin)

            record_admin_audit_log(
                session,
                action="workspace_created",
                status="succeeded",
                request=request,
                admin_account_id=admin_account.id,
                target_type="workspace",
                target_id=str(tenant.id),
                detail=build_workspace_creation_detail(
                    actor_user_id=admin_account.user_id,
                    workspace_name=tenant.name,
                    workspace_id=tenant.id,
                    workspace_slug=tenant.slug,
                ),
            )
        session.refresh(tenant)
        return tenant
    except HTTPException as exc:
        session.rollback()
        record_admin_audit_log(
            session,
            action="workspace_creation_failed",
            status="failed",
            request=request,
            admin_account_id=admin_account.id,
            target_type="workspace",
            target_id=None,
            detail=build_workspace_creation_detail(
                actor_user_id=admin_account.user_id,
                workspace_name=workspace_input.name,
                reason=str(exc.detail),
            ),
        )
        session.commit()
        raise
    except IntegrityError as exc:
        session.rollback()
        record_admin_audit_log(
            session,
            action="workspace_creation_failed",
            status="failed",
            request=request,
            admin_account_id=admin_account.id,
            target_type="workspace",
            target_id=None,
            detail=build_workspace_creation_detail(
                actor_user_id=admin_account.user_id,
                workspace_name=workspace_input.name,
                reason="duplicate_key",
            ),
        )
        session.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workspace could not be created") from exc
    except Exception as exc:
        session.rollback()
        record_admin_audit_log(
            session,
            action="workspace_creation_failed",
            status="failed",
            request=request,
            admin_account_id=admin_account.id,
            target_type="workspace",
            target_id=None,
            detail=build_workspace_creation_detail(
                actor_user_id=admin_account.user_id,
                workspace_name=workspace_input.name,
                reason="database_failure",
            ),
        )
        session.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Workspace creation failed") from exc


def delete_workspace_as_admin(
    session: Session,
    admin_account: AdminAccount,
    workspace_id: int,
    request: Request | None = None,
) -> Tenant:
    ensure_admin_can_create_workspace(admin_account)
    workspace = get_workspace_by_id(session, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if workspace.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workspace is already deleted")

    record_admin_audit_log(
        session,
        action="workspace_deletion_started",
        status="started",
        request=request,
        admin_account_id=admin_account.id,
        target_type="workspace",
        target_id=str(workspace.id),
        detail=build_workspace_creation_detail(
            actor_user_id=admin_account.user_id,
            workspace_name=workspace.name,
            workspace_id=workspace.id,
            workspace_slug=workspace.slug,
        ),
    )
    session.commit()

    try:
        with session.begin():
            locked_workspace = get_workspace_by_id(session, workspace_id)
            if locked_workspace is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
            if locked_workspace.deleted_at is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workspace is already deleted")

            locked_workspace.deleted_at = datetime.now(UTC)
            session.add(locked_workspace)

            record_admin_audit_log(
                session,
                action="workspace_deleted",
                status="succeeded",
                request=request,
                admin_account_id=admin_account.id,
                target_type="workspace",
                target_id=str(locked_workspace.id),
                detail=build_workspace_creation_detail(
                    actor_user_id=admin_account.user_id,
                    workspace_name=locked_workspace.name,
                    workspace_id=locked_workspace.id,
                    workspace_slug=locked_workspace.slug,
                ),
            )
        session.refresh(locked_workspace)
        return locked_workspace
    except HTTPException as exc:
        session.rollback()
        record_admin_audit_log(
            session,
            action="workspace_deletion_failed",
            status="failed",
            request=request,
            admin_account_id=admin_account.id,
            target_type="workspace",
            target_id=str(workspace_id),
            detail=build_workspace_creation_detail(
                actor_user_id=admin_account.user_id,
                workspace_name=workspace.name,
                workspace_id=workspace.id,
                workspace_slug=workspace.slug,
                reason=str(exc.detail),
            ),
        )
        session.commit()
        raise
    except Exception as exc:
        session.rollback()
        record_admin_audit_log(
            session,
            action="workspace_deletion_failed",
            status="failed",
            request=request,
            admin_account_id=admin_account.id,
            target_type="workspace",
            target_id=str(workspace_id),
            detail=build_workspace_creation_detail(
                actor_user_id=admin_account.user_id,
                workspace_name=workspace.name,
                workspace_id=workspace.id,
                workspace_slug=workspace.slug,
                reason="database_failure",
            ),
        )
        session.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Workspace deletion failed") from exc
