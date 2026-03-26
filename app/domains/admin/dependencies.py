from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.db.session import get_db_session
from app.domains.admin_auth.models import AdminAccount
from app.domains.admin_auth.models import AdminRole
from app.domains.admin_auth.service import get_admin_account_by_id
from app.domains.admin_auth.tokens import AdminTokenType
from app.domains.admin_auth.tokens import decode_admin_token


def require_development_admin_access(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> str:
    settings = get_settings()
    if not settings.is_local_env or not settings.dev_admin_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Development admin authentication is disabled in this environment",
        )
    admin_api_key = settings.admin_api_key
    if x_admin_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-Admin-Key header")
    if not admin_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin access not configured")
    if x_admin_key != admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")
    return x_admin_key


def get_current_admin_principal(
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: Session = Depends(get_db_session),
) -> AdminAccount:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    payload = decode_admin_token(token, expected_token_type=AdminTokenType.access)
    try:
        admin_account_id = int(str(payload["sub"]))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from None
    admin_account = get_admin_account_by_id(session, admin_account_id)
    if admin_account is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    if admin_account.user_id != int(payload["user_id"]) or admin_account.user.email != payload["email"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    if not admin_account.is_active or not admin_account.user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is inactive")
    return admin_account


def require_admin_access(admin_account: AdminAccount = Depends(get_current_admin_principal)) -> AdminAccount:
    return admin_account


def require_superadmin_access(admin_account: AdminAccount = Depends(get_current_admin_principal)) -> AdminAccount:
    if admin_account.role != AdminRole.superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin role required")
    return admin_account
