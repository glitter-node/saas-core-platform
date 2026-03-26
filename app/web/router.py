from pathlib import Path

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse

from app.config.settings import get_settings

router = APIRouter(tags=["web"])

BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "pages"


@router.get("/", include_in_schema=False)
def landing_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "landing.html")


@router.get("/login", include_in_schema=False)
def user_login_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "user_login.html")


@router.get("/dashboard", include_in_schema=False)
def user_dashboard_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "user_dashboard.html")


@router.get("/magic-link/complete", include_in_schema=False)
def magic_link_complete_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "magic_link_complete.html")


@router.get("/admin/login", include_in_schema=False)
def admin_login_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "admin_login.html")


@router.get("/admin/dashboard", include_in_schema=False)
def admin_dashboard_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "admin_dashboard.html")


@router.get("/web-config.js", include_in_schema=False)
def web_config() -> Response:
    settings = get_settings()
    body = (
        "window.SAAS_CONFIG = "
        + "{"
        + f'appName: "{settings.app_name}", '
        + f'appDomain: "{settings.app_domain}", '
        + f'docsEnabled: {str(settings.docs_enabled).lower()}'
        + "};"
    )
    return Response(content=body, media_type="application/javascript")
