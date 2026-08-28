from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient
from models.image import StoredImage
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
    assert [image["id"] for image in paginated_response.json()] == [
        str(IMAGE_IDS[1])
    ]
