from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from models.image import StoredImage
from routers.images import MAX_IMAGE_SIZE_BYTES
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

CAPTURED_AT = "2026-08-29T12:34:56Z"


async def _get_stored_image(
    connection: AsyncConnection,
    image_id: UUID,
) -> StoredImage | None:
    async with AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    ) as session:
        return await session.get(StoredImage, image_id)


def test_create_image_stores_upload_and_returns_image_details(
    client: TestClient,
    db_connection: AsyncConnection,
) -> None:
    image_data = b"fake png data"

    response = client.post(
        "/api/v1/images",
        files={"image": ("captures/robot.png", image_data, "image/png")},
        data={
            "device_id": "robot-7",
            "captured_at": CAPTURED_AT,
            "metadata": '{"camera": "front", "battery": 87}',
        },
    )

    assert response.status_code == 201
    image = response.json()
    assert image["filename"] == "robot.png"
    assert image["content_type"] == "image/png"
    assert image["metadata"] == {"camera": "front", "battery": 87}
    assert image["device_id"] == "robot-7"
    expected_captured_at = datetime.fromisoformat(CAPTURED_AT)
    assert datetime.fromisoformat(image["captured_at"]) == expected_captured_at
    assert image["created_at"]
    assert image["updated_at"]
    assert "image_data" not in image

    assert client.portal is not None
    stored_image = client.portal.call(
        _get_stored_image,
        db_connection,
        UUID(image["id"]),
    )
    assert stored_image is not None
    assert stored_image.image_data == image_data


def test_create_image_rejects_unsupported_content_type(client: TestClient) -> None:
    response = client.post(
        "/api/v1/images",
        files={"image": ("image.gif", b"gif data", "image/gif")},
        data={
            "device_id": "robot-1",
            "captured_at": CAPTURED_AT,
        },
    )

    assert response.status_code == 415
    assert response.json() == {
        "detail": "Supported image types are JPEG, PNG, and WebP"
    }


@pytest.mark.parametrize(
    ("metadata", "expected_detail"),
    [
        ("{invalid", "metadata must be valid JSON"),
        ("[]", "metadata must be a JSON object"),
    ],
)
def test_create_image_rejects_invalid_metadata(
    client: TestClient,
    metadata: str,
    expected_detail: str,
) -> None:
    response = client.post(
        "/api/v1/images",
        files={"image": ("image.jpg", b"jpeg data", "image/jpeg")},
        data={
            "device_id": "robot-1",
            "captured_at": CAPTURED_AT,
            "metadata": metadata,
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": expected_detail}


def test_create_image_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        "/api/v1/images",
        files={"image": ("empty.webp", b"", "image/webp")},
        data={
            "device_id": "robot-1",
            "captured_at": CAPTURED_AT,
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Image file must not be empty"}


def test_create_image_rejects_file_larger_than_10_mb(client: TestClient) -> None:
    response = client.post(
        "/api/v1/images",
        files={
            "image": (
                "large.jpg",
                b"x" * (MAX_IMAGE_SIZE_BYTES + 1),
                "image/jpeg",
            )
        },
        data={
            "device_id": "robot-1",
            "captured_at": CAPTURED_AT,
        },
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Image exceeds the 10 MB size limit"}
