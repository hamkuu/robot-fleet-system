import json
from datetime import datetime
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from database import get_db
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from models.image import StoredImage
from schemas.image import ImageRead, ImageUpdate
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/images", tags=["images"])

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _image_response(image: StoredImage) -> ImageRead:
    return ImageRead(
        id=image.id,
        filename=image.filename,
        content_type=image.content_type,
        metadata=image.image_metadata,
        device_id=image.device_id,
        captured_at=image.captured_at,
        created_at=image.created_at,
        updated_at=image.updated_at,
    )


async def _read_image_data(upload: UploadFile) -> bytes:
    image_data = bytearray()

    while True:
        remaining_bytes = MAX_IMAGE_SIZE_BYTES - len(image_data)
        chunk = await upload.read(min(UPLOAD_CHUNK_SIZE_BYTES, remaining_bytes + 1))
        if not chunk:
            break

        image_data.extend(chunk)
        if len(image_data) > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Image exceeds the 10 MB size limit",
            )

    if not image_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Image file must not be empty",
        )

    return bytes(image_data)


@router.get("", response_model=list[ImageRead])
async def list_images(
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ImageRead]:
    statement = (
        select(
            StoredImage.id,
            StoredImage.filename,
            StoredImage.content_type,
            StoredImage.image_metadata.label("metadata"),
            StoredImage.device_id,
            StoredImage.captured_at,
            StoredImage.created_at,
            StoredImage.updated_at,
        )
        .order_by(StoredImage.captured_at.desc(), StoredImage.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(statement)

    return [ImageRead.model_validate(row) for row in result.mappings().all()]


@router.get("/{image_id}", response_model=ImageRead)
async def get_image(
    image_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ImageRead:
    statement = select(
        StoredImage.id,
        StoredImage.filename,
        StoredImage.content_type,
        StoredImage.image_metadata.label("metadata"),
        StoredImage.device_id,
        StoredImage.captured_at,
        StoredImage.created_at,
        StoredImage.updated_at,
    ).where(StoredImage.id == image_id)
    result = await session.execute(statement)
    image = result.mappings().one_or_none()

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    return ImageRead.model_validate(image)


@router.patch("/{image_id}", response_model=ImageRead)
async def update_image(
    image_id: UUID,
    image_update: ImageUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ImageRead:
    updated_fields = image_update.model_dump(exclude_unset=True)
    if "metadata" in updated_fields:
        updated_fields["image_metadata"] = updated_fields.pop("metadata")

    statement = (
        update(StoredImage)
        .where(StoredImage.id == image_id)
        .values(**updated_fields)
        .returning(
            StoredImage.id,
            StoredImage.filename,
            StoredImage.content_type,
            StoredImage.image_metadata.label("metadata"),
            StoredImage.device_id,
            StoredImage.captured_at,
            StoredImage.created_at,
            StoredImage.updated_at,
        )
    )
    result = await session.execute(statement)
    image = result.mappings().one_or_none()

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    await session.commit()
    return ImageRead.model_validate(image)


@router.get("/{image_id}/content", response_class=Response)
async def get_image_content(
    image_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    statement = select(
        StoredImage.image_data,
        StoredImage.filename,
        StoredImage.content_type,
    ).where(StoredImage.id == image_id)
    result = await session.execute(statement)
    image = result.one_or_none()

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    encoded_filename = quote(image.filename, safe="")
    return Response(
        content=image.image_data,
        media_type=image.content_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
async def create_image(
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP image")],
    device_id: Annotated[str, Form(min_length=1)],
    captured_at: Annotated[datetime, Form()],
    session: Annotated[AsyncSession, Depends(get_db)],
    metadata: Annotated[str, Form()] = "{}",
) -> ImageRead:
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported image types are JPEG, PNG, and WebP",
        )

    try:
        image_metadata = json.loads(metadata)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="metadata must be valid JSON",
        ) from error

    if not isinstance(image_metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="metadata must be a JSON object",
        )

    filename = (image.filename or "image").replace("\\", "/").rsplit("/", 1)[-1]

    try:
        image_data = await _read_image_data(image)
    finally:
        await image.close()

    stored_image = StoredImage(
        image_data=image_data,
        filename=filename,
        content_type=image.content_type,
        image_metadata=image_metadata,
        device_id=device_id,
        captured_at=captured_at,
    )
    session.add(stored_image)
    await session.commit()
    await session.refresh(stored_image)

    return _image_response(stored_image)
