from pydantic import BaseModel, field_validator


class WorkspaceCreateInput(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Workspace name is required")
        if len(normalized) > 120:
            raise ValueError("Workspace name must be 120 characters or fewer")
        return normalized
