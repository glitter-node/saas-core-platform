from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.admin_auth.models import AdminRole


class AdminLoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=255)
    otp_code: str | None = Field(default=None, min_length=1, max_length=32)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if "@" not in normalized_value or normalized_value.startswith("@") or normalized_value.endswith("@"):
            raise ValueError("Invalid email address")
        return normalized_value


class AdminRefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class AdminMagicLinkStartRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if "@" not in normalized_value or normalized_value.startswith("@") or normalized_value.endswith("@"):
            raise ValueError("Invalid email address")
        return normalized_value


class AdminMagicLinkConsumeRequest(BaseModel):
    token: str = Field(min_length=1)


class AdminMagicLinkStartResponse(BaseModel):
    detail: str


class AdminLogoutResponse(BaseModel):
    detail: str


class AdminPrincipalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role: AdminRole
    email: str
    full_name: str
    is_active: bool
    mfa_enabled: bool
    last_admin_login_at: datetime | None


class AdminTokenPairRead(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    admin: AdminPrincipalRead


class AdminRefreshTokenRead(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
