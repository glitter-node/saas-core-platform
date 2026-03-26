from pydantic import BaseModel, ConfigDict

from app.domains.memberships.models import MembershipRole
from app.domains.users.schemas import UserRead


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MembershipRole
    user: UserRead


class MembershipInviteCreate(BaseModel):
    email: str
    full_name: str
    role: MembershipRole
