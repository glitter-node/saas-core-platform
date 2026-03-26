from pydantic import BaseModel, ConfigDict

from app.domains.subscriptions.schemas import PlanRead


class UsageMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current: int
    limit: int | None
    remaining: int | None


class UsageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan: PlanRead
    counters: dict[str, int]
    limits: dict[str, int | None]
    remaining: dict[str, int | None]
    metrics: dict[str, UsageMetricRead]
