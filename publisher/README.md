# Image Publisher

This command-line client publishes a JPEG, PNG, or WebP image to Mosquitto as a single MessagePack
message. Run it on the computer or capture device that has access to the image.

## Usage

Start the broker, database, subscriber, and API from the repository root:

```bash
docker compose up -d mqtt-broker db mqtt-subscriber backend
```

Publish an image:

```bash
cd publisher
uv run python publish_image.py \
  --broker localhost \
  --device-id amr01-camera \
  --metadata '{"title":"Linux Logo"}' \
  images/linux_logo.png

uv run python publish_image.py \
  --broker localhost \
  --device-id user-phone \
  --metadata '{"title":"AMR"}' \
  images/amr.jpg
  

```

The publisher generates a UUID and capture timestamp and sends the message with MQTT QoS 1 to:

```text
images/{device_id}/captures
```

Check ingestion from the repository root:

```bash
docker compose logs --tail 30 mqtt-subscriber
curl http://localhost:8000/api/v1/images
```

If the publisher runs on another device, replace `localhost` with the IP address or hostname of the
computer running Mosquitto. Port `1883` must be reachable from that device.
