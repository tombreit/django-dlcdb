# README.container

## podman

```bash
podman build --tag podman-dlcdb  --file container/Containerfile .
podman run --tty --interactive --publish 8000:8000 --name podman-dlcdb --rm podman-dlcdb
# mount volume in development: --volume .:/code
podman exec -ti podman-dlcdb bash
```

