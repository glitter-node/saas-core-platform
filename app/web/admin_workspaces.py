from html import escape
from pathlib import Path
from urllib.parse import parse_qs
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.domains.admin_audit.service import record_admin_audit_log
from app.domains.admin.dependencies import require_admin_access
from app.domains.admin_auth.models import AdminAccount
from app.domains.admin_workspaces.service import create_workspace_as_admin

router = APIRouter(tags=["web-admin-workspaces"])

BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "pages"
ADMIN_WORKSPACE_NEW_TEMPLATE = PAGES_DIR / "admin_workspace_new.html"


def render_admin_workspace_new_page(*, name: str = "", status_message: str = "", status_code: int = 200) -> HTMLResponse:
    template = ADMIN_WORKSPACE_NEW_TEMPLATE.read_text(encoding="utf-8")
    body = (
        template
        .replace("__WORKSPACE_NAME__", escape(name))
        .replace("__WORKSPACE_STATUS__", escape(status_message))
    )
    return HTMLResponse(content=body, status_code=status_code)


@router.get("/admin/workspaces/new", include_in_schema=False)
def admin_workspace_new_page(
    request: Request,
    admin: AdminAccount = Depends(require_admin_access),
    session: Session = Depends(get_db_session),
) -> HTMLResponse:
    record_admin_audit_log(
        session,
        action="workspace_creation_page_rendered",
        status="succeeded",
        request=request,
        admin_account_id=admin.id,
        target_type="workspace",
        target_id=None,
    )
    session.commit()
    return render_admin_workspace_new_page()


@router.post("/admin/workspaces", include_in_schema=False, response_model=None)
async def create_workspace_route(
    request: Request,
    admin: AdminAccount = Depends(require_admin_access),
    session: Session = Depends(get_db_session),
) -> HTMLResponse:
    body = await request.body()
    payload = parse_qs(body.decode("utf-8"))
    name = payload.get("name", [""])[0]
    try:
        workspace = create_workspace_as_admin(
            session,
            admin,
            {"name": name},
            request=request,
        )
    except Exception as exc:
        detail = getattr(exc, "detail", "Request failed")
        status_code = getattr(exc, "status_code", 500)
        return render_admin_workspace_new_page(name=name, status_message=str(detail), status_code=status_code)

    query = urlencode(
        {
            "workspace_created": workspace.subdomain,
            "workspace_name": workspace.name,
        }
    )
    return RedirectResponse(url=f"/admin/dashboard?{query}", status_code=303)
