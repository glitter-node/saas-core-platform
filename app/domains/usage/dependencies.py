from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_tenant
from app.db.session import get_db_session
from app.domains.auth.dependencies import require_member
from app.domains.memberships.models import Membership
from app.domains.tenants.models import Tenant
from app.domains.usage.service import API_REQUESTS, track_metric


def track_api_request_usage(
    tenant: Tenant = Depends(require_tenant),
    membership: Membership = Depends(require_member),
    session: Session = Depends(get_db_session),
) -> None:
    track_metric(session, tenant.id, API_REQUESTS, 1)
    session.commit()
