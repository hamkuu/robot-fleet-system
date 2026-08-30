from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/png", "image/webp")


class MqttImageMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    captured_at: datetime
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    metadata: dict[str, Any] = Field(default_factory=dict)
    image_data: Annotated[
        bytes,
        Field(min_length=1, max_length=MAX_IMAGE_SIZE_BYTES),
    ]

    @field_validator("captured_at")
    @classmethod
    def captured_at_must_have_timezone(cls, captured_at: datetime) -> datetime:
        if captured_at.utcoffset() is None:
            raise ValueError("captured_at must include a timezone offset")
        return captured_at

    @field_validator("filename")
    @classmethod
    def filename_must_not_contain_a_path(cls, filename: str) -> str:
        if filename in {".", ".."} or "/" in filename or "\\" in filename:
            raise ValueError("filename must not contain a path")
        return filename

    @field_validator("image_data")
    @classmethod
    def image_data_must_match_content_type(
        cls,
        image_data: bytes,
        info,
    ) -> bytes:
        content_type = info.data.get("content_type")
        signatures = {
            "image/jpeg": image_data.startswith(b"\xff\xd8\xff"),
            "image/png": image_data.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/webp": (
                len(image_data) >= 12
                and image_data.startswith(b"RIFF")
                and image_data[8:12] == b"WEBP"
            ),
        }
        if content_type in signatures and not signatures[content_type]:
            raise ValueError(f"image data does not match {content_type}")
        return image_data
