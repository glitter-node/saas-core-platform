from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domains.organizations.models import Organization


def build_organization_query(tenant_id: int) -> Select[tuple[Organization]]:
    return select(Organization).where(Organization.tenant_id == tenant_id)


def get_organization(session: Session, tenant_id: int) -> Organization | None:
    return session.execute(build_organization_query(tenant_id)).scalar_one_or_none()
