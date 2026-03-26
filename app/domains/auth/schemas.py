from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.memberships.models import MembershipRole
from app.domains.tenants.schemas import TenantRead
from app.domains.users.schemas import UserRead


class MeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserRead
    tenant: TenantRead
    role: MembershipRole


class RegisterRequest(BaseModel):
    email: str
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if "@" not in normalized_value or normalized_value.startswith("@") or normalized_value.endswith("@"):
            raise ValueError("Invalid email address")
        return normalized_value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Full name is required")
        return normalized_value


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if "@" not in normalized_value or normalized_value.startswith("@") or normalized_value.endswith("@"):
            raise ValueError("Invalid email address")
        return normalized_value


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class MagicLinkStartRequest(BaseModel):
    email: str
    tenant_subdomain: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if "@" not in normalized_value or normalized_value.startswith("@") or normalized_value.endswith("@"):
            raise ValueError("Invalid email address")
        return normalized_value

    @field_validator("tenant_subdomain")
    @classmethod
    def validate_tenant_subdomain(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value = value.strip().lower()
        if not normalized_value:
            return None
        return normalized_value


class MagicLinkConsumeRequest(BaseModel):
    token: str = Field(min_length=1)


class MagicLinkStartResponse(BaseModel):
    detail: str


class TenantOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    subdomain: str


class UserEntryDiscoveryRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if "@" not in normalized_value or normalized_value.startswith("@") or normalized_value.endswith("@"):
            raise ValueError("Invalid email address")
        return normalized_value


class UserEntryDiscoveryResponse(BaseModel):
    mode: str
    detail: str
    tenants: list[TenantOptionRead]
    example_tenants: list[TenantOptionRead]


class TenantExamplesResponse(BaseModel):
    tenants: list[TenantOptionRead]


class AuthenticatedUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    is_active: bool
    last_login_at: datetime | None


class TokenPairRead(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: AuthenticatedUserRead


class AccessTokenRead(BaseModel):
    access_token: str
    token_type: str


class RefreshTokenRead(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class LogoutResponse(BaseModel):
    detail: str
