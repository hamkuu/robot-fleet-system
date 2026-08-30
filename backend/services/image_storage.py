from enum import StrEnum

from models.image import StoredImage
from schemas.mqtt_image import MqttImageMessage
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


class StoreResult(StrEnum):
    INSERTED = "inserted"
    DUPLICATE = "duplicate"


class ConflictingImageIdError(Exception):
    pass


async def store_mqtt_image(
    session: AsyncSession,
    message: MqttImageMessage,
    device_id: str,
) -> StoreResult:
    statement = (
        insert(StoredImage)
        .values(
            id=message.id,
            image_data=message.image_data,
            filename=message.filename,
            content_type=message.content_type,
            image_metadata=message.metadata,
            device_id=device_id,
            captured_at=message.captured_at,
        )
        .on_conflict_do_nothing(index_elements=[StoredImage.id])
        .returning(StoredImage.id)
    )
    result = await session.execute(statement)

    if result.scalar_one_or_none() is not None:
        await session.commit()
        return StoreResult.INSERTED

    existing = await session.get(StoredImage, message.id)
    if existing is None:
        raise RuntimeError("duplicate image disappeared before it could be verified")

    same_capture = (
        existing.image_data == message.image_data
        and existing.filename == message.filename
        and existing.content_type == message.content_type
        and existing.image_metadata == message.metadata
        and existing.device_id == device_id
        and existing.captured_at == message.captured_at
    )
    if not same_capture:
        raise ConflictingImageIdError(
            f"image id {message.id} already belongs to a different capture"
        )

    await session.commit()
    return StoreResult.DUPLICATE
