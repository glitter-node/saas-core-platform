import re

from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.config.settings import get_settings
from app.db import models
from app.db.session import SessionLocal, engine
from app.middleware.tenant_context import TenantContextMiddleware
from app.web.router import router as web_router


_DENY_RE = re.compile(
    r"""
    (?ix)
    (?!^/\.well-known/)
    (?:
        ^/(?:app|venv|\.vscode)(?:/|$)
      | ^/data/config(?:/|$)
      | (?:^|/)
        (?:
            \.env(?:\.[^/]+)?
          | \.(?:git|hg|svn)(?:/|$)
          | \.(?:DS_Store|htaccess|htpasswd)$
          | \.aws/credentials$
          | \.ssh/(?:id_rsa|id_ed25519|authorized_keys|known_hosts)$
          | (?:_conf_|_config)\.py$
          | .*?\.(?:py|pyc|pyo)$
          | .*?\.(?:log|bak|old|swp|tmp|orig|save)$
          | .*~
          | .*?\.(?:sql|sqlite|db)$
          | .*?\.(?:pem|key|p12|pfx|kdbx)$
        )
        (?:$|/)
    )
    """.strip(),
)

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


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'self'; "
        "object-src 'none'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "worker-src 'self' blob:",
    )
    response.headers.setdefault(
        "Permissions-Policy",
        "accelerometer=(),camera=(),geolocation=(),gyroscope=(),"
        "magnetometer=(),microphone=(),payment=(),usb=(),browsing-topics=()",
    )
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    return response


@app.middleware("http")
async def deny_sensitive_paths(request: Request, call_next) -> Response:
    if _DENY_RE.search(request.url.path):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return await call_next(request)


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict[str, str]:
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")
    return {"status": "ok", "environment": settings.app_env}
