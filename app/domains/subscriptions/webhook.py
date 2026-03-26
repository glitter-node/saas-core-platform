from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.domains.subscriptions.service import (
    apply_checkout_session_completed,
    apply_stripe_subscription_event,
    create_billing_event_ledger_entry,
    mark_billing_event_processed,
)
from app.domains.subscriptions.stripe_client import StripeClient, get_object_value

router = APIRouter(prefix="/webhooks/stripe", tags=["webhooks"])


@router.post("", status_code=status.HTTP_200_OK)
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> Response:
    if stripe_signature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header")

    payload = await request.body()
    stripe_client = StripeClient()
    if not stripe_client.webhook_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe webhook is not configured")
    try:
        event = stripe_client.construct_event(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe webhook signature") from exc

    event_type = get_object_value(event, "type")
    event_id = get_object_value(event, "id")
    event_data = get_object_value(event, "data")
    event_object = get_object_value(event_data, "object") if event_data is not None else None
    if not isinstance(event_id, str) or not event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe event payload")
    if not isinstance(event_type, str) or not event_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe event payload")

    with SessionLocal() as session:
        with session.begin():
            try:
                ledger_entry = create_billing_event_ledger_entry(session, event_id, event_type)
            except IntegrityError as exc:
                if _is_duplicate_key_error(exc):
                    return Response(status_code=status.HTTP_200_OK)
                raise
            _apply_webhook_event(session, event_type, event_object)
            mark_billing_event_processed(ledger_entry)

    return Response(status_code=status.HTTP_200_OK)


def _apply_webhook_event(session: Session, event_type: str, event_object: object | None) -> None:
    if event_object is None:
        return
    if event_type == "checkout.session.completed":
        apply_checkout_session_completed(session, event_object)
        return
    if event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        apply_stripe_subscription_event(session, event_object)


def _is_duplicate_key_error(error: IntegrityError) -> bool:
    original = getattr(error, "orig", None)
    args = getattr(original, "args", ())
    return bool(args) and args[0] == 1062
