from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status


def get_current_tenant(request: Request) -> Any:
    return getattr(request.state, "tenant", None)


def require_tenant(request: Request) -> Any:
    tenant = get_current_tenant(request)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant context not found")
    return tenant


class PublicAPIRouter(APIRouter):
    pass


class TenantAPIRouter(APIRouter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        dependencies = list(kwargs.pop("dependencies", []))
        dependencies.append(Depends(require_tenant))
        kwargs["dependencies"] = dependencies
        super().__init__(*args, **kwargs)


class AdminAPIRouter(APIRouter):
    pass
