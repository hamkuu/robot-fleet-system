from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from models.image import StoredImage
from routers.images import MAX_IMAGE_SIZE_BYTES
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

IMAGE_IDS = [
    UUID("00000000-0000-0000-0000-000000000001"),
    UUID("00000000-0000-0000-0000-000000000002"),
    UUID("00000000-0000-0000-0000-000000000003"),
]


async def _seed_images(connection: AsyncConnection) -> None:
    async with AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    ) as session:
        session.add_all(
            [
                StoredImage(
                    id=IMAGE_IDS[index],
                    image_data=f"image-{index}".encode(),
                    filename=f"image-{index}.jpg",
                    content_type="image/jpeg",
                    image_metadata={"sequence": index},
                    device_id="robot-1",
                    captured_at=datetime(2026, 8, 29, index, tzinfo=timezone.utc),
                )
                for index in range(3)
            ]
        )
        await session.commit()


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


def test_list_images_returns_newest_first_and_supports_pagination(
    client: TestClient,
    db_connection: AsyncConnection,
) -> None:
    assert client.portal is not None
    client.portal.call(_seed_images, db_connection)

    response = client.get("/api/v1/images")

    assert response.status_code == 200
    images = response.json()
    assert [image["id"] for image in images] == [
        str(IMAGE_IDS[2]),
        str(IMAGE_IDS[1]),
        str(IMAGE_IDS[0]),
    ]
    assert images[0]["filename"] == "image-2.jpg"
    assert images[0]["content_type"] == "image/jpeg"
    assert images[0]["metadata"] == {"sequence": 2}
    assert images[0]["device_id"] == "robot-1"
    assert "image_data" not in images[0]

    paginated_response = client.get("/api/v1/images", params={"limit": 1, "offset": 1})

    assert paginated_response.status_code == 200
    assert [image["id"] for image in paginated_response.json()] == [str(IMAGE_IDS[1])]


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
            "captured_at": "2026-08-29T12:34:56Z",
            "metadata": '{"camera": "front", "battery": 87}',
        },
    )

    assert response.status_code == 201
    image = response.json()
    assert image["filename"] == "robot.png"
    assert image["content_type"] == "image/png"
    assert image["metadata"] == {"camera": "front", "battery": 87}
    assert image["device_id"] == "robot-7"
    assert datetime.fromisoformat(image["captured_at"]) == datetime(
        2026,
        8,
        29,
        12,
        34,
        56,
        tzinfo=timezone.utc,
    )
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
            "captured_at": "2026-08-29T12:34:56Z",
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
            "captured_at": "2026-08-29T12:34:56Z",
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
            "captured_at": "2026-08-29T12:34:56Z",
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
            "captured_at": "2026-08-29T12:34:56Z",
        },
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Image exceeds the 10 MB size limit"}
