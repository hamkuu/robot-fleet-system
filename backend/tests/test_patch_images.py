from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from models.image import StoredImage
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

IMAGE_ID = UUID("00000000-0000-0000-0000-000000000001")
MISSING_IMAGE_ID = UUID("00000000-0000-0000-0000-000000000099")


async def _seed_image(connection: AsyncConnection) -> None:
    async with AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    ) as session:
        session.add(
            StoredImage(
                id=IMAGE_ID,
                image_data=b"image-data",
                filename="original.jpg",
                content_type="image/jpeg",
                image_metadata={"camera": "front", "reviewed": False},
                device_id="robot-1",
                captured_at=datetime(2026, 8, 29, tzinfo=timezone.utc),
            )
        )
        await session.commit()


def test_patch_image_updates_filename_and_preserves_other_fields(
    client: TestClient,
    db_connection: AsyncConnection,
) -> None:
    assert client.portal is not None
    client.portal.call(_seed_image, db_connection)

    response = client.patch(
        f"/api/v1/images/{IMAGE_ID}",
        json={"filename": "renamed.jpg"},
    )

    assert response.status_code == 200
    image = response.json()
    assert image["filename"] == "renamed.jpg"
    assert image["metadata"] == {"camera": "front", "reviewed": False}
    assert image["content_type"] == "image/jpeg"
    assert image["device_id"] == "robot-1"

    content_response = client.get(f"/api/v1/images/{IMAGE_ID}/content")
    assert content_response.status_code == 200
    assert content_response.content == b"image-data"
    assert content_response.headers["content-disposition"] == (
        "inline; filename*=UTF-8''renamed.jpg"
    )


def test_patch_image_replaces_metadata_and_preserves_filename(
    client: TestClient,
    db_connection: AsyncConnection,
) -> None:
    assert client.portal is not None
    client.portal.call(_seed_image, db_connection)

    response = client.patch(
        f"/api/v1/images/{IMAGE_ID}",
        json={"metadata": {"reviewed": True}},
    )

    assert response.status_code == 200
    image = response.json()
    assert image["filename"] == "original.jpg"
    assert image["metadata"] == {"reviewed": True}

    get_response = client.get(f"/api/v1/images/{IMAGE_ID}")
    assert get_response.status_code == 200
    assert get_response.json()["metadata"] == {"reviewed": True}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"filename": ""},
        {"filename": None},
        {"metadata": None},
        {"device_id": "robot-2"},
    ],
)
def test_patch_image_rejects_invalid_updates(
    client: TestClient,
    payload: dict[str, object],
) -> None:
    response = client.patch(f"/api/v1/images/{IMAGE_ID}", json=payload)

    assert response.status_code == 422


def test_patch_image_returns_not_found(client: TestClient) -> None:
    response = client.patch(
        f"/api/v1/images/{MISSING_IMAGE_ID}",
        json={"filename": "renamed.jpg"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Image not found"}
