from fastapi import Depends

from app.api.dependencies import TenantAPIRouter, require_tenant
from app.domains.auth.dependencies import get_current_user, require_member
from app.domains.auth.schemas import MeRead
from app.domains.memberships.models import Membership
from app.domains.tenants.models import Tenant
from app.domains.tenants.schemas import TenantRead
from app.domains.usage.dependencies import track_api_request_usage
from app.domains.users.models import User
from app.domains.users.schemas import UserRead

router = TenantAPIRouter(prefix="", tags=["auth"])


@router.get("/me", response_model=MeRead, dependencies=[Depends(track_api_request_usage)])
def get_me(
    tenant: Tenant = Depends(require_tenant),
    user: User = Depends(get_current_user),
    membership: Membership = Depends(require_member),
) -> MeRead:
    return MeRead(
        user=UserRead.model_validate(user),
        tenant=TenantRead.model_validate(tenant),
        role=membership.role,
    )
