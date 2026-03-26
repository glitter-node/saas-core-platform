from fastapi import Depends, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import PublicAPIRouter
from app.db.session import get_db_session
from app.domains.admin_auth.schemas import AdminMagicLinkConsumeRequest
from app.domains.admin_auth.schemas import AdminMagicLinkStartRequest
from app.domains.admin_auth.schemas import AdminMagicLinkStartResponse
from app.domains.admin_auth.schemas import AdminLoginRequest
from app.domains.admin_auth.schemas import AdminLogoutResponse
from app.domains.admin_auth.schemas import AdminPrincipalRead
from app.domains.admin_auth.schemas import AdminRefreshTokenRead
from app.domains.admin_auth.schemas import AdminRefreshTokenRequest
from app.domains.admin_auth.schemas import AdminTokenPairRead
from app.domains.admin_auth.service import consume_admin_magic_link
from app.domains.admin_auth.service import login_admin
from app.domains.admin_auth.service import logout_admin
from app.domains.admin_auth.service import refresh_admin_access_token
from app.domains.admin_auth.service import send_admin_magic_link

public_router = PublicAPIRouter(prefix="/admin/auth", tags=["admin-auth"])


@public_router.post("/login", response_model=AdminTokenPairRead, status_code=status.HTTP_200_OK)
def login(
    payload: AdminLoginRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> AdminTokenPairRead:
    return AdminTokenPairRead.model_validate(login_admin(session, payload.email, payload.password, payload.otp_code, request))


@public_router.post("/magic-link/start", response_model=AdminMagicLinkStartResponse)
def start_magic_link(
    payload: AdminMagicLinkStartRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> AdminMagicLinkStartResponse:
    send_admin_magic_link(session, payload.email, request)
    return AdminMagicLinkStartResponse(detail="If the address is allowed, a sign-in link has been sent")


@public_router.post("/magic-link/consume", response_model=AdminTokenPairRead)
def consume_magic_link_route(
    payload: AdminMagicLinkConsumeRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> AdminTokenPairRead:
    return AdminTokenPairRead.model_validate(consume_admin_magic_link(session, payload.token, request))


@public_router.post("/refresh", response_model=AdminRefreshTokenRead)
def refresh(
    payload: AdminRefreshTokenRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> AdminRefreshTokenRead:
    return AdminRefreshTokenRead.model_validate(refresh_admin_access_token(session, payload.refresh_token, request))


@public_router.post("/logout", response_model=AdminLogoutResponse)
def logout(
    payload: AdminRefreshTokenRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> AdminLogoutResponse:
    logout_admin(session, payload.refresh_token, request)
    return AdminLogoutResponse(detail="Logout acknowledged")
