from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    subdomain: str
    status: str
    created_at: datetime
    updated_at: datetime
