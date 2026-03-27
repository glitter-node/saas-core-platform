from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from app.config.settings import get_settings
from app.web.admin_workspaces import router as admin_workspaces_web_router

router = APIRouter(tags=["web"])
router.include_router(admin_workspaces_web_router)

BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "pages"
settings = get_settings()
FAVICON_PATH = settings.assets_root_path / "gimg" / "favicon" / "favicon.ico"
ROBOTS_PATH = settings.assets_root_path / "saasapi.glitter.kr_robots.txt"
SITEMAP_PATH = settings.assets_root_path / "saasapi.glitter.kr_sitemap.xml"


@router.get("/", include_in_schema=False)
def landing_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "landing.html")


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    if FAVICON_PATH.exists():
        return FileResponse(FAVICON_PATH, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Not Found")


@router.head("/favicon.ico", include_in_schema=False)
def favicon_head() -> FileResponse:
    if FAVICON_PATH.exists():
        return FileResponse(FAVICON_PATH, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Not Found")


@router.get("/robots.txt", include_in_schema=False)
def robots_txt() -> FileResponse:
    if ROBOTS_PATH.exists():
        return FileResponse(ROBOTS_PATH, media_type="text/plain; charset=utf-8")
    raise HTTPException(status_code=404, detail="Not Found")


@router.head("/robots.txt", include_in_schema=False)
def robots_txt_head() -> FileResponse:
    if ROBOTS_PATH.exists():
        return FileResponse(ROBOTS_PATH, media_type="text/plain; charset=utf-8")
    raise HTTPException(status_code=404, detail="Not Found")


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml() -> FileResponse:
    if SITEMAP_PATH.exists():
        return FileResponse(SITEMAP_PATH, media_type="application/xml")
    raise HTTPException(status_code=404, detail="Not Found")


@router.head("/sitemap.xml", include_in_schema=False)
def sitemap_xml_head() -> FileResponse:
    if SITEMAP_PATH.exists():
        return FileResponse(SITEMAP_PATH, media_type="application/xml")
    raise HTTPException(status_code=404, detail="Not Found")


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
    body = (
        "window.SAAS_CONFIG = "
        + "{"
        + f'appName: "{settings.app_name}", '
        + f'appDomain: "{settings.app_domain}", '
        + f'docsEnabled: {str(settings.docs_enabled).lower()}'
        + "};"
    )
    return Response(content=body, media_type="application/javascript")
