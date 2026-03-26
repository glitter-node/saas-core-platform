import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from fastapi import HTTPException, status

from app.config.settings import get_settings
from app.domains.admin_auth.models import AdminAccount


class AdminTokenType(StrEnum):
    access = "admin_access"
    refresh = "admin_refresh"


def create_admin_access_token(admin_account: AdminAccount) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.admin_access_token_expire_minutes)
    return encode_admin_token(
        {
            "sub": str(admin_account.id),
            "user_id": admin_account.user_id,
            "email": admin_account.user.email,
            "scope": settings.admin_jwt_scope,
            "token_type": AdminTokenType.access.value,
            "exp": int(expires_at.timestamp()),
        }
    )


def create_admin_refresh_token(
    admin_account: AdminAccount,
    *,
    session_nonce: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[str, datetime]:
    settings = get_settings()
    refresh_expires_at = expires_at or (datetime.now(timezone.utc) + timedelta(days=settings.admin_refresh_token_expire_days))
    token = encode_admin_token(
        {
            "sub": str(admin_account.id),
            "user_id": admin_account.user_id,
            "email": admin_account.user.email,
            "scope": settings.admin_jwt_scope,
            "token_type": AdminTokenType.refresh.value,
            "exp": int(refresh_expires_at.timestamp()),
            "jti": session_nonce or secrets.token_urlsafe(24),
        }
    )
    return token, refresh_expires_at


def decode_admin_token(token: str, expected_token_type: AdminTokenType | None = None) -> dict[str, str | int]:
    settings = get_settings()
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError:
        raise _invalid_token_error("Malformed token") from None

    header_bytes = _urlsafe_b64decode(encoded_header)
    if header_bytes is None:
        raise _invalid_token_error("Malformed token header")
    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _invalid_token_error("Malformed token header") from None
    if not isinstance(header, dict):
        raise _invalid_token_error("Malformed token header")
    if header.get("alg") != settings.jwt_algorithm or header.get("typ") != "JWT":
        raise _invalid_token_error("Invalid token header")

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = _sign(signing_input, settings.secret_key)
    provided_signature = _urlsafe_b64decode(encoded_signature)
    if provided_signature is None or not hmac.compare_digest(provided_signature, expected_signature):
        raise _invalid_token_error("Invalid token signature")

    payload_bytes = _urlsafe_b64decode(encoded_payload)
    if payload_bytes is None:
        raise _invalid_token_error("Malformed token payload")
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _invalid_token_error("Malformed token payload") from None
    if not isinstance(payload, dict):
        raise _invalid_token_error("Malformed token payload")

    token_type = payload.get("token_type")
    if token_type not in {AdminTokenType.access.value, AdminTokenType.refresh.value}:
        raise _invalid_token_error("Invalid token type")
    if expected_token_type is not None and token_type != expected_token_type.value:
        raise _invalid_token_error("Invalid token type")

    scope = payload.get("scope")
    if scope != settings.admin_jwt_scope:
        raise _invalid_token_error("Invalid token scope")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise _invalid_token_error("Invalid token expiry")
    if datetime.now(timezone.utc).timestamp() >= exp:
        raise _invalid_token_error("Token has expired")

    subject = payload.get("sub")
    user_id = payload.get("user_id")
    email = payload.get("email")
    if not isinstance(subject, str) or not subject:
        raise _invalid_token_error("Invalid token subject")
    if not isinstance(user_id, int):
        raise _invalid_token_error("Invalid token subject")
    if not isinstance(email, str) or not email:
        raise _invalid_token_error("Invalid token email")

    return {
        "sub": subject,
        "user_id": user_id,
        "email": email,
        "scope": scope,
        "token_type": token_type,
        "exp": exp,
    }


def encode_admin_token(payload: dict[str, str | int]) -> str:
    settings = get_settings()
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    encoded_header = _urlsafe_b64encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    encoded_payload = _urlsafe_b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = _urlsafe_b64encode(_sign(signing_input, settings.secret_key))
    return f"{encoded_header}.{encoded_payload}.{signature}"


def _sign(value: bytes, secret_key: str) -> bytes:
    return hmac.new(secret_key.encode("utf-8"), value, hashlib.sha256).digest()


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes | None:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return None


def _invalid_token_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
