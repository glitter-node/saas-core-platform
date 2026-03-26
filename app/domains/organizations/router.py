from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import TenantAPIRouter, require_tenant
from app.db.session import get_db_session
from app.domains.organizations.schemas import OrganizationRead
from app.domains.organizations.service import get_organization
from app.domains.tenants.models import Tenant

router = TenantAPIRouter(prefix="/organization", tags=["organization"])


@router.get("", response_model=OrganizationRead)
def get_current_organization(
    tenant: Tenant = Depends(require_tenant),
    session: Session = Depends(get_db_session),
) -> OrganizationRead:
    organization = get_organization(session, tenant.id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationRead.model_validate(organization)
