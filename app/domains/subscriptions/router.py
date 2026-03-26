from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import TenantAPIRouter, require_tenant
from app.db.session import get_db_session
from app.domains.auth.dependencies import require_member, require_owner
from app.domains.memberships.models import Membership
from app.domains.subscriptions.schemas import CheckoutSessionCreate, CheckoutSessionRead, SubscriptionRead
from app.domains.subscriptions.service import ensure_subscription, get_billable_price_id, get_checkout_urls
from app.domains.subscriptions.stripe_client import StripeClient
from app.domains.tenants.models import Tenant
from app.domains.usage.dependencies import track_api_request_usage

router = TenantAPIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription", response_model=SubscriptionRead, dependencies=[Depends(track_api_request_usage)])
def get_current_subscription(
    tenant: Tenant = Depends(require_tenant),
    membership: Membership = Depends(require_member),
    session: Session = Depends(get_db_session),
) -> SubscriptionRead:
    subscription = ensure_subscription(session, tenant.id)
    session.commit()
    session.refresh(subscription)
    return SubscriptionRead.model_validate(subscription)


@router.post("/checkout-session", response_model=CheckoutSessionRead)
def create_checkout_session(
    payload: CheckoutSessionCreate,
    request: Request,
    tenant: Tenant = Depends(require_tenant),
    membership: Membership = Depends(require_owner),
    session: Session = Depends(get_db_session),
) -> CheckoutSessionRead:
    price_id = get_billable_price_id(payload.plan_code)
    if price_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan is not billable")

    subscription = ensure_subscription(session, tenant.id)
    stripe_client = StripeClient()
    success_url, cancel_url = get_checkout_urls(request.headers["host"], request.url.scheme)
    checkout_session = stripe_client.create_checkout_session(
        customer_email=membership.user.email,
        customer_id=subscription.stripe_customer_id,
        price_id=price_id,
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        plan_code=payload.plan_code,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    session.commit()
    url = getattr(checkout_session, "url", None)
    if not isinstance(url, str):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stripe checkout session did not return a URL")
    return CheckoutSessionRead(url=url)
