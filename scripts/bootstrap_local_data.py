from app.db import models
from app.db.session import SessionLocal
from app.domains.auth.passwords import hash_password
from app.domains.memberships.models import MembershipRole
from app.domains.memberships.service import create_membership, get_membership_by_tenant_and_user
from app.domains.notifications.models import Notification
from app.domains.organizations.models import Organization
from app.domains.subscriptions.service import ensure_subscription
from app.domains.tenants.models import Tenant
from app.domains.usage.service import API_REQUESTS, ensure_usage_counter, set_counter
from app.domains.users.service import create_user, get_user_by_email


TENANT_NAME = "Local Demo"
TENANT_SLUG = "localdemo"
OWNER_EMAIL = "owner@app.local"
OWNER_PASSWORD = "StrongPass123"
OWNER_NAME = "Local Owner"


def main() -> None:
    _ = models
    with SessionLocal() as session:
        tenant = session.query(Tenant).filter(Tenant.slug == TENANT_SLUG).one_or_none()
        if tenant is None:
            tenant = Tenant(name=TENANT_NAME, slug=TENANT_SLUG, subdomain=TENANT_SLUG, status="active")
            session.add(tenant)
            session.flush()
            session.add(Organization(tenant_id=tenant.id, name=TENANT_NAME))

        user = get_user_by_email(session, OWNER_EMAIL)
        if user is None:
            user = create_user(
                session=session,
                email=OWNER_EMAIL,
                full_name=OWNER_NAME,
                password_hash=hash_password(OWNER_PASSWORD),
                is_active=True,
            )
        else:
            user.password_hash = hash_password(OWNER_PASSWORD)
            user.is_active = True
            session.add(user)

        membership = get_membership_by_tenant_and_user(session, tenant.id, user.id)
        if membership is None:
            create_membership(session, tenant.id, user, MembershipRole.owner)

        ensure_subscription(session, tenant.id)
        ensure_usage_counter(session, tenant.id, API_REQUESTS)
        set_counter(session, tenant.id, API_REQUESTS, 799, enqueue_warning=False)
        session.query(Notification).filter(Notification.tenant_id == tenant.id).delete()
        session.commit()

    print(f"tenant={TENANT_SLUG}")
    print(f"email={OWNER_EMAIL}")
    print(f"password={OWNER_PASSWORD}")


if __name__ == "__main__":
    main()
