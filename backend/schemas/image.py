from datetime import datetime
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    metadata: dict[str, Any]
    device_id: str
    captured_at: datetime
    created_at: datetime
    updated_at: datetime


class ImageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: Annotated[str | None, Field(min_length=1)] = None
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Updated fields must not be null")

        return self
