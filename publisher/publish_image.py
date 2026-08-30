import argparse
import json
import re
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import msgpack
from paho.mqtt import client as mqtt
from paho.mqtt.publish import single

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
CONTENT_TYPES_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class PublisherInputError(ValueError):
    pass


def read_metadata(raw_metadata: str) -> dict[str, Any]:
    try:
        metadata = json.loads(raw_metadata)
    except json.JSONDecodeError as error:
        raise PublisherInputError("metadata must be valid JSON") from error

    if not isinstance(metadata, dict):
        raise PublisherInputError("metadata must be a JSON object")
    return metadata


def read_image(image_path: Path) -> tuple[bytes, str]:
    if not image_path.is_file():
        raise PublisherInputError(f"image does not exist: {image_path}")

    content_type = CONTENT_TYPES_BY_SUFFIX.get(image_path.suffix.lower())
    if content_type is None:
        supported = ", ".join(sorted(CONTENT_TYPES_BY_SUFFIX))
        raise PublisherInputError(f"supported image extensions are: {supported}")

    image_size = image_path.stat().st_size
    if image_size == 0:
        raise PublisherInputError("image must not be empty")
    if image_size > MAX_IMAGE_SIZE_BYTES:
        raise PublisherInputError("image exceeds the 10 MB size limit")

    image_data = image_path.read_bytes()
    if len(image_data) > MAX_IMAGE_SIZE_BYTES:
        raise PublisherInputError("image exceeds the 10 MB size limit")

    signatures = {
        "image/jpeg": image_data.startswith(b"\xff\xd8\xff"),
        "image/png": image_data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": (
            len(image_data) >= 12
            and image_data.startswith(b"RIFF")
            and image_data[8:12] == b"WEBP"
        ),
    }
    if not signatures[content_type]:
        raise PublisherInputError(
            f"file contents do not match the {content_type} extension"
        )

    return image_data, content_type


def build_payload(
    image_id: UUID,
    image_path: Path,
    image_data: bytes,
    content_type: str,
    metadata: dict[str, Any],
) -> bytes:
    message = {
        "id": str(image_id),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "filename": image_path.name,
        "content_type": content_type,
        "metadata": metadata,
        "image_data": image_data,
    }
    return msgpack.packb(message, use_bin_type=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a JPEG, PNG, or WebP capture through MQTT.",
    )
    parser.add_argument("image", type=Path, help="Path to the image to publish")
    parser.add_argument("--device-id", required=True, help="Camera device identifier")
    parser.add_argument("--broker", default="localhost", help="MQTT broker hostname")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument(
        "--metadata",
        default="{}",
        help='JSON object, for example \'{"subject":"robot"}\'',
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if not DEVICE_ID_PATTERN.fullmatch(args.device_id):
        raise PublisherInputError(
            "device ID may contain only letters, numbers, dots, underscores, and hyphens"
        )
    if not 1 <= args.port <= 65535:
        raise PublisherInputError("port must be between 1 and 65535")

    metadata = read_metadata(args.metadata)
    image_path = args.image.expanduser().resolve()
    image_data, content_type = read_image(image_path)
    image_id = uuid4()
    topic = f"images/{args.device_id}/captures"
    payload = build_payload(
        image_id=image_id,
        image_path=image_path,
        image_data=image_data,
        content_type=content_type,
        metadata=metadata,
    )

    client_id = f"image-publisher-{args.device_id}-{str(image_id)[:8]}"
    try:
        single(
            topic=topic,
            payload=payload,
            qos=1,
            retain=False,
            hostname=args.broker,
            port=args.port,
            client_id=client_id,
        )
    except (mqtt.MQTTException, OSError) as error:
        raise RuntimeError(
            f"could not publish to MQTT broker {args.broker}:{args.port}"
        ) from error

    print(f"Published image {image_id}")
    print(f"Topic: {topic}")
    print(f"File: {image_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PublisherInputError, RuntimeError) as error:
        raise SystemExit(f"error: {error}") from error
