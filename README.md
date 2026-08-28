# Robot Fleet System

Distributed Robot Fleet System.

## Getting-started

```bash
docker compose build
docker compose up
```

## Reset

```bash
docker system prune -a
docker volume prune -a
```

## Image Model

| Field          | PostgreSQL type | Description                                                      |
|----------------|-----------------|------------------------------------------------------------------|
| `id`           | `UUID`          | Unique identifier used to retrieve, update, or delete the image. |
| `image_data`   | `BYTEA`         | Binary contents of the image.                                    |
| `filename`     | `TEXT`          | Original or user-facing filename, including its extension.       |
| `content_type` | `TEXT`          | Image MIME type, such as `image/jpeg` or `image/png`.            |
| `metadata`     | `JSONB`         | User-editable metadata, such as a title or description.          |
| `device_id`    | `TEXT`          | Identifier of the camera device that captured the image.         |
| `captured_at`  | `TIMESTAMPTZ`   | Time when the camera device captured the image.                  |
| `created_at`   | `TIMESTAMPTZ`   | Time when the image was initially stored.                        |
| `updated_at`   | `TIMESTAMPTZ`   | Time when the image or its metadata was last modified.           |
