from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.dependencies import TenantAPIRouter, require_tenant
from app.db.session import get_db_session
from app.domains.auth.dependencies import require_member
from app.domains.memberships.models import Membership
from app.domains.subscriptions.schemas import PlanRead
from app.domains.tenants.models import Tenant
from app.domains.usage.schemas import UsageMetricRead, UsageRead
from app.domains.usage.service import get_usage_snapshot

router = TenantAPIRouter(prefix="/usage", tags=["usage"])


@router.get("", response_model=UsageRead)
def get_usage_summary(
    tenant: Tenant = Depends(require_tenant),
    membership: Membership = Depends(require_member),
    session: Session = Depends(get_db_session),
) -> UsageRead:
    plan, counters, limits, remaining = get_usage_snapshot(session, tenant.id)
    session.commit()
    metrics = {
        metric_code: UsageMetricRead(
            current=counters.get(metric_code, 0),
            limit=limits.get(metric_code),
            remaining=remaining.get(metric_code),
        )
        for metric_code in counters
    }
    return UsageRead(
        plan=PlanRead.model_validate(plan),
        counters=counters,
        limits=limits,
        remaining=remaining,
        metrics=metrics,
    )
