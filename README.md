# Robot Fleet System | Image Capture

Image Capture in Distributed Robot Fleet System.

## User Story

As a warehouse operator, I want to capture or select images on a phone or computer and upload them
to the central fleet system, so that authorized users can view and manage the images in one place.

## Live Demo

Image Management UI available on [fleet.hamkuu.com](https://fleet.hamkuu.com)

Image Publish Command:

```bash
cd publisher
uv run python publish_image.py \
  --broker broker.fleet.hamkuu.com \
  --device-id user-phone \
  --metadata '{"title":"AMRs"}' \
  images/amrs.png
```

(Assume source IP address is allowed in VPC Firewall)

## Getting-started Locally

```bash
docker compose build
docker compose up
```

## Local Services

- [Index UI on Backend](http://localhost:8000/)
- [Backend OpenAPI docs](http://localhost:8000/docs)
- [Database Adminer](http://localhost:8010)

## Sub-README Files

- [backend/README.md](backend/README.md) provides further details of backend service
- [publisher/README.md](publisher/README.md) explains how to publish an image via MQTT
