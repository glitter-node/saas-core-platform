from fastapi import APIRouter

from app.api.dependencies import AdminAPIRouter, PublicAPIRouter, TenantAPIRouter
from app.domains.admin.router import router as admin_router_metrics
from app.domains.admin_auth.router import public_router as admin_auth_public_router
from app.domains.auth.me_router import router as me_router
from app.domains.auth.router import public_router as auth_public_router
from app.domains.auth.router import tenant_router as auth_tenant_router
from app.domains.memberships.router import router as memberships_router
from app.domains.organizations.router import router as organizations_router
from app.domains.subscriptions.router import router as subscriptions_router
from app.domains.subscriptions.webhook import router as stripe_webhook_router
from app.domains.tenants.router import router as tenants_router
from app.domains.usage.router import router as usage_router

api_router = APIRouter()
public_router = PublicAPIRouter()
tenant_router = TenantAPIRouter()
admin_router = AdminAPIRouter()

public_router.include_router(auth_public_router)
public_router.include_router(admin_auth_public_router)
public_router.include_router(stripe_webhook_router)
tenant_router.include_router(tenants_router)
tenant_router.include_router(me_router)
tenant_router.include_router(auth_tenant_router)
tenant_router.include_router(organizations_router)
tenant_router.include_router(memberships_router)
tenant_router.include_router(subscriptions_router)
tenant_router.include_router(usage_router)
admin_router.include_router(admin_router_metrics)

api_router.include_router(public_router)
api_router.include_router(tenant_router)
api_router.include_router(admin_router)
