from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from database import Base
from sqlalchemy import DateTime, Index, LargeBinary, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class StoredImage(Base):
    __tablename__ = "images"
    __table_args__ = (
        Index("ix_images_device_id_captured_at", "device_id", "captured_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    image_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    image_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    device_id: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
