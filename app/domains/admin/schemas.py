from datetime import datetime

from pydantic import BaseModel


class AdminOverviewRead(BaseModel):
    total_tenants: int
    active_tenants: int
    total_users: int
    total_memberships: int
    active_subscriptions: int
    plan_distribution: dict[str, int]
    notifications_count: int


class AdminRevenueRead(BaseModel):
    active_paid_subscriptions: int
    estimated_mrr: int
    currency: str
    pricing: dict[str, int]


class AdminRecentTenantRead(BaseModel):
    id: int
    name: str
    subdomain: str
    status: str
    created_at: datetime
