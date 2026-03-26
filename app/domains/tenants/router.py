from fastapi import Request

from app.api.dependencies import TenantAPIRouter
from app.domains.tenants.schemas import TenantRead

router = TenantAPIRouter(prefix="/tenant", tags=["tenant"])


@router.get("", response_model=TenantRead)
def get_current_tenant(request: Request) -> TenantRead:
    return TenantRead.model_validate(request.state.tenant)
