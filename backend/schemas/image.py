from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
