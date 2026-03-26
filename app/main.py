from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.config.settings import get_settings
from app.db import models
from app.db.session import SessionLocal, engine
from app.middleware.tenant_context import TenantContextMiddleware
from app.web.router import router as web_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug if settings.is_local_env else False,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key", "X-User-Email", "Stripe-Signature"],
)
app.add_middleware(TenantContextMiddleware, session_factory=SessionLocal)
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
app.include_router(api_router, prefix="/api/v1")
app.include_router(web_router)


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict[str, str]:
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")
    return {"status": "ok", "environment": settings.app_env}
