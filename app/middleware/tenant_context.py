from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config.settings import get_settings
from app.domains.tenants.service import get_active_tenant_by_subdomain


class TenantContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, session_factory):
        super().__init__(app)
        self.session_factory = session_factory
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        request.state.tenant = None
        request.state.tenant_id = None
        request.state.tenant_subdomain = self._extract_subdomain(request.headers.get("host"))

        if request.state.tenant_subdomain:
            with self.session_factory() as session:
                tenant = get_active_tenant_by_subdomain(session, request.state.tenant_subdomain)
                request.state.tenant = tenant
                request.state.tenant_id = tenant.id if tenant else None

        return await call_next(request)

    def _extract_subdomain(self, host_header: str | None) -> str | None:
        if not host_header:
            return None

        host = host_header.split(":", 1)[0].lower()
        root_domain = self.settings.app_domain.lower()

        if host == root_domain:
            return None

        suffix = f".{root_domain}"
        if not host.endswith(suffix):
            return None

        subdomain = host[: -len(suffix)]
        return subdomain or None
