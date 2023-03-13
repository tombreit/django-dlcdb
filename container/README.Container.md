# README.container

## podman

```bash
podman build \
    --tag podman-dlcdb  \
    --file container/Containerfile .

podman run \
    --tty --interactive \
    --publish 8000:8000 \
    --volume ./run/db:/app/run/db:Z \
    --volume ./run/media:/app/run/media:Z \
    --volume ./dlcdb:/app/dlcdb:Z \
    --name podman-dlcdb --rm podman-dlcdb

#     --volume ./dlcdb:/app/dlcdb:Z \
# mount run dir: --volume ./run:/app/run
# mount code dir in development: --volume .:/app

podman exec -ti podman-dlcdb bash
```

