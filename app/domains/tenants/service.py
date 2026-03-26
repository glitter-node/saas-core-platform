from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domains.tenants.models import Tenant


def build_active_tenant_query(subdomain: str) -> Select[tuple[Tenant]]:
    return select(Tenant).where(Tenant.subdomain == subdomain, Tenant.status == "active")


def get_active_tenant_by_subdomain(session: Session, subdomain: str) -> Tenant | None:
    return session.execute(build_active_tenant_query(subdomain)).scalar_one_or_none()


def build_active_tenants_query(limit: int | None = None) -> Select[tuple[Tenant]]:
    query = select(Tenant).where(Tenant.status == "active").order_by(Tenant.created_at.desc(), Tenant.id.desc())
    if limit is not None:
        query = query.limit(limit)
    return query


def list_active_tenants(session: Session, limit: int | None = None) -> list[Tenant]:
    return list(session.execute(build_active_tenants_query(limit)).scalars().all())
