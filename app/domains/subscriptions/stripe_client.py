from collections.abc import Mapping

import stripe

from app.config.settings import get_settings


class StripeClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = stripe.StripeClient(settings.stripe_secret_key)
        self.webhook_secret = settings.stripe_webhook_secret

    def create_checkout_session(
        self,
        *,
        customer_email: str,
        customer_id: str | None,
        price_id: str,
        tenant_id: int,
        tenant_slug: str,
        plan_code: str,
        success_url: str,
        cancel_url: str,
    ) -> object:
        payload = {
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "line_items": [{"price": price_id, "quantity": 1}],
            "allow_promotion_codes": True,
            "metadata": {"tenant_id": str(tenant_id), "tenant_slug": tenant_slug, "plan_code": plan_code},
            "subscription_data": {
                "metadata": {"tenant_id": str(tenant_id), "tenant_slug": tenant_slug, "plan_code": plan_code}
            },
        }
        if customer_id:
            payload["customer"] = customer_id
        else:
            payload["customer_email"] = customer_email
        return self.client.checkout.sessions.create(payload)

    def construct_event(self, payload: bytes, signature: str) -> object:
        return stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=self.webhook_secret)


def get_stripe_client() -> StripeClient:
    return StripeClient()


def get_object_value(data: Mapping[str, object] | object, key: str) -> object | None:
    if isinstance(data, Mapping):
        return data.get(key)
    getter = getattr(data, "get", None)
    if callable(getter):
        try:
            return getter(key)
        except Exception:
            pass
    try:
        return getattr(data, key)
    except Exception:
        return None
