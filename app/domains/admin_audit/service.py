from collections.abc import Mapping

from fastapi import Request
from sqlalchemy.orm import Session

from app.domains.admin_audit.models import AdminAuditLog


def extract_request_metadata(request: Request | None) -> dict[str, str | None]:
    if request is None:
        return {"ip_address": None, "user_agent": None}
    client = request.client
    user_agent = request.headers.get("User-Agent")
    return {
        "ip_address": client.host if client is not None else None,
        "user_agent": user_agent if user_agent else None,
    }


def record_admin_audit_log(
    session: Session,
    *,
    action: str,
    status: str,
    request: Request | None = None,
    admin_account_id: int | None = None,
    auth_session_id: int | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: Mapping[str, object] | None = None,
) -> AdminAuditLog:
    metadata = extract_request_metadata(request)
    audit_log = AdminAuditLog(
        admin_account_id=admin_account_id,
        auth_session_id=auth_session_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=metadata["ip_address"],
        user_agent=metadata["user_agent"],
        status=status,
        detail_json=dict(detail) if detail is not None else None,
    )
    session.add(audit_log)
    session.flush()
    return audit_log
