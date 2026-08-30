import asyncio
import logging
import re

import aiomqtt
import msgpack
from config import settings
from database import AsyncSessionLocal, Base, engine
from models.image import StoredImage  # noqa: F401
from pydantic import ValidationError
from schemas.mqtt_image import MAX_IMAGE_SIZE_BYTES, MqttImageMessage
from services.image_storage import (
    ConflictingImageIdError,
    StoreResult,
    store_mqtt_image,
)
from sqlalchemy.exc import SQLAlchemyError

LOGGER = logging.getLogger(__name__)
TOPIC_PATTERN = re.compile(r"^images/(?P<device_id>[A-Za-z0-9._-]+)/captures$")
MAX_MQTT_PAYLOAD_SIZE_BYTES = MAX_IMAGE_SIZE_BYTES + 64 * 1024
RECONNECT_DELAY_SECONDS = 5
DATABASE_RETRY_DELAY_SECONDS = 5


def decode_message(payload: bytes) -> MqttImageMessage:
    if len(payload) > MAX_MQTT_PAYLOAD_SIZE_BYTES:
        raise ValueError("MQTT payload exceeds the permitted size")

    unpacked = msgpack.unpackb(
        payload,
        raw=False,
        strict_map_key=True,
        max_bin_len=MAX_IMAGE_SIZE_BYTES,
        max_str_len=64 * 1024,
        max_array_len=1024,
        max_map_len=1024,
        max_ext_len=1024,
    )
    return MqttImageMessage.model_validate(unpacked)


def device_id_from_topic(topic: str) -> str:
    match = TOPIC_PATTERN.fullmatch(topic)
    if match is None:
        raise ValueError(f"unexpected MQTT topic: {topic}")
    return match.group("device_id")


async def persist_message(message: MqttImageMessage, device_id: str) -> StoreResult:
    while True:
        try:
            async with AsyncSessionLocal() as session:
                return await store_mqtt_image(session, message, device_id)
        except SQLAlchemyError:
            LOGGER.exception(
                "Database write failed for image %s; retrying in %s seconds",
                message.id,
                DATABASE_RETRY_DELAY_SECONDS,
            )
            await asyncio.sleep(DATABASE_RETRY_DELAY_SECONDS)


async def handle_message(mqtt_message: aiomqtt.Message) -> None:
    topic = str(mqtt_message.topic)
    try:
        device_id = device_id_from_topic(topic)
        message = decode_message(mqtt_message.payload)
        result = await persist_message(message, device_id)
    except (msgpack.UnpackException, ValueError, ValidationError):
        LOGGER.exception("Discarding invalid image message from topic %s", topic)
        return
    except ConflictingImageIdError:
        LOGGER.exception("Discarding conflicting image message from topic %s", topic)
        return

    LOGGER.info(
        "%s image %s from device %s",
        "Stored" if result == StoreResult.INSERTED else "Ignored duplicate",
        message.id,
        device_id,
    )


async def initialize_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def consume_messages() -> None:
    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.MQTT_HOST,
                port=settings.MQTT_PORT,
                identifier=settings.MQTT_CLIENT_ID,
            ) as client:
                await client.subscribe(settings.MQTT_TOPIC, qos=1)
                LOGGER.info(
                    "Subscribed to %s on %s:%s",
                    settings.MQTT_TOPIC,
                    settings.MQTT_HOST,
                    settings.MQTT_PORT,
                )
                async for message in client.messages:
                    await handle_message(message)
        except aiomqtt.MqttError:
            LOGGER.exception(
                "MQTT connection failed; reconnecting in %s seconds",
                RECONNECT_DELAY_SECONDS,
            )
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)


async def main() -> None:
    await initialize_database()
    try:
        await consume_messages()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
