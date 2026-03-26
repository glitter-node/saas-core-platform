from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import AdminAPIRouter
from app.db.session import get_db_session
from app.domains.admin.dependencies import require_admin_access
from app.domains.admin.schemas import AdminOverviewRead, AdminRecentTenantRead, AdminRevenueRead
from app.domains.admin.service import get_admin_overview, get_admin_revenue, list_recent_tenants
from app.domains.admin_audit.service import record_admin_audit_log
from app.domains.admin_auth.models import AdminAccount

router = AdminAPIRouter(prefix="/admin/metrics", tags=["admin"])


@router.get("/overview", response_model=AdminOverviewRead)
def get_metrics_overview(
    request: Request,
    admin: AdminAccount = Depends(require_admin_access),
    session: Session = Depends(get_db_session),
) -> AdminOverviewRead:
    record_admin_audit_log(
        session,
        action="admin_metrics_overview_accessed",
        status="succeeded",
        request=request,
        admin_account_id=admin.id,
        target_type="admin_account",
        target_id=str(admin.id),
    )
    session.commit()
    return AdminOverviewRead.model_validate(get_admin_overview(session))


@router.get("/revenue", response_model=AdminRevenueRead)
def get_metrics_revenue(
    request: Request,
    admin: AdminAccount = Depends(require_admin_access),
    session: Session = Depends(get_db_session),
) -> AdminRevenueRead:
    record_admin_audit_log(
        session,
        action="admin_metrics_revenue_accessed",
        status="succeeded",
        request=request,
        admin_account_id=admin.id,
        target_type="admin_account",
        target_id=str(admin.id),
    )
    session.commit()
    return AdminRevenueRead.model_validate(get_admin_revenue(session))


@router.get("/recent-tenants", response_model=list[AdminRecentTenantRead])
def get_recent_tenants(
    request: Request,
    admin: AdminAccount = Depends(require_admin_access),
    session: Session = Depends(get_db_session),
) -> list[AdminRecentTenantRead]:
    record_admin_audit_log(
        session,
        action="admin_recent_tenants_accessed",
        status="succeeded",
        request=request,
        admin_account_id=admin.id,
        target_type="admin_account",
        target_id=str(admin.id),
    )
    session.commit()
    return [AdminRecentTenantRead.model_validate(tenant, from_attributes=True) for tenant in list_recent_tenants(session)]
