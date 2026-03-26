from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    limits_json: dict


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    current_period_end: datetime | None
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    plan: PlanRead


class CheckoutSessionCreate(BaseModel):
    plan_code: str


class CheckoutSessionRead(BaseModel):
    url: str
