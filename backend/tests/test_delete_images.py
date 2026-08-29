from datetime import datetime, timezone
from uuid import UUID

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
                filename="image.jpg",
                content_type="image/jpeg",
                image_metadata={"camera": "front"},
                device_id="robot-1",
                captured_at=datetime(2026, 8, 29, tzinfo=timezone.utc),
            )
        )
        await session.commit()


def test_delete_image_removes_metadata_and_content(
    client: TestClient,
    db_connection: AsyncConnection,
) -> None:
    assert client.portal is not None
    client.portal.call(_seed_image, db_connection)

    response = client.delete(f"/api/v1/images/{IMAGE_ID}")

    assert response.status_code == 204
    assert response.content == b""
    assert "content-type" not in response.headers

    metadata_response = client.get(f"/api/v1/images/{IMAGE_ID}")
    content_response = client.get(f"/api/v1/images/{IMAGE_ID}/content")
    assert metadata_response.status_code == 404
    assert content_response.status_code == 404


def test_delete_image_returns_not_found(client: TestClient) -> None:
    response = client.delete(f"/api/v1/images/{MISSING_IMAGE_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Image not found"}


def test_delete_image_rejects_invalid_uuid(client: TestClient) -> None:
    response = client.delete("/api/v1/images/not-a-uuid")

    assert response.status_code == 422
