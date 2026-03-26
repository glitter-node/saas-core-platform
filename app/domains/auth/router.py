from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import PublicAPIRouter, TenantAPIRouter
from app.domains.auth.dependencies import get_current_user
from app.domains.auth.schemas import AuthenticatedUserRead
from app.domains.auth.schemas import LoginRequest
from app.domains.auth.schemas import MagicLinkConsumeRequest
from app.domains.auth.schemas import MagicLinkStartRequest
from app.domains.auth.schemas import MagicLinkStartResponse
from app.domains.auth.schemas import LogoutResponse
from app.domains.auth.schemas import RefreshTokenRead
from app.domains.auth.schemas import RefreshTokenRequest
from app.domains.auth.schemas import RegisterRequest
from app.domains.auth.schemas import TokenPairRead
from app.domains.auth.schemas import TenantExamplesResponse
from app.domains.auth.schemas import UserEntryDiscoveryRequest
from app.domains.auth.schemas import UserEntryDiscoveryResponse
from app.domains.auth.service import consume_user_magic_link
from app.domains.auth.service import discover_user_entry
from app.domains.auth.service import get_tenant_examples
from app.domains.auth.service import login_user
from app.domains.auth.service import logout_user
from app.domains.auth.service import refresh_access_token
from app.domains.auth.service import register_user
from app.domains.auth.service import resolve_magic_link_tenant
from app.domains.auth.service import send_user_magic_link
from app.domains.users.models import User
from app.db.session import get_db_session

public_router = PublicAPIRouter(prefix="/auth", tags=["auth"])
tenant_router = TenantAPIRouter(prefix="/auth", tags=["auth"])


@public_router.post("/register", response_model=AuthenticatedUserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    session: Session = Depends(get_db_session),
) -> AuthenticatedUserRead:
    user = register_user(session, payload.email, payload.full_name, payload.password)
    return AuthenticatedUserRead.model_validate(user)


@public_router.post("/login", response_model=TokenPairRead)
def login(
    payload: LoginRequest,
    session: Session = Depends(get_db_session),
) -> TokenPairRead:
    return TokenPairRead.model_validate(login_user(session, payload.email, payload.password))


@public_router.post("/discover", response_model=UserEntryDiscoveryResponse)
def discover_entry(
    payload: UserEntryDiscoveryRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> UserEntryDiscoveryResponse:
    return UserEntryDiscoveryResponse.model_validate(discover_user_entry(session, payload.email, request))


@public_router.get("/tenant-examples", response_model=TenantExamplesResponse)
def tenant_examples(session: Session = Depends(get_db_session)) -> TenantExamplesResponse:
    return TenantExamplesResponse.model_validate({"tenants": get_tenant_examples(session)})


@public_router.post("/magic-link/start", response_model=MagicLinkStartResponse)
def start_magic_link(
    payload: MagicLinkStartRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> MagicLinkStartResponse:
    tenant = resolve_magic_link_tenant(session, request, payload.tenant_subdomain)
    send_user_magic_link(session, tenant, payload.email, request)
    return MagicLinkStartResponse(detail="Check your email for the sign-in link")


@public_router.post("/magic-link/consume", response_model=TokenPairRead)
def consume_magic_link_route(
    payload: MagicLinkConsumeRequest,
    session: Session = Depends(get_db_session),
) -> TokenPairRead:
    return TokenPairRead.model_validate(consume_user_magic_link(session, payload.token))


@public_router.post("/refresh", response_model=RefreshTokenRead)
def refresh(
    payload: RefreshTokenRequest,
    session: Session = Depends(get_db_session),
) -> RefreshTokenRead:
    return RefreshTokenRead.model_validate(refresh_access_token(session, payload.refresh_token))


@public_router.post("/logout", response_model=LogoutResponse)
def logout(
    payload: RefreshTokenRequest,
    session: Session = Depends(get_db_session),
) -> LogoutResponse:
    logout_user(session, payload.refresh_token)
    return LogoutResponse(detail="Logout acknowledged")


@tenant_router.get("/session")
def get_session_context(
    request: Request,
    user: User = Depends(get_current_user),
) -> dict[str, str | int]:
    tenant = request.state.tenant
    return {"tenant_slug": tenant.slug, "tenant_id": tenant.id, "user_id": user.id}
