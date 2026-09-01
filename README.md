# Robot Fleet System | Image Capture

Image Capture in Distributed Robot Fleet System.

## User Story

As a warehouse operator, I want to capture or select images on a phone or computer and upload them
to the central fleet system, so that authorized users can view and manage the images in one place.

## Getting-started

```bash
docker compose build
docker compose up
```

## Accessible Services

- [Index UI on Backend](http://localhost:8000/)
- [Backend OpenAPI docs](http://localhost:8000/docs)
- [Database Adminer](http://localhost:8010)

## Sub-README Files

- [backend/README.md](backend/README.md) provides further details of backend service
- [publisher/README.md](publisher/README.md) explains how to publish an image via MQTT
