# README.container

## podman

```bash
podman build \
    --tag dlcdb  \
    --file container/Containerfile .

podman run \
    --name podman-dlcdb \
    --tty --interactive \
    --publish 8000:8000 \
    --volume ./data:/app/data \
    --rm \
    dlcdb
```
