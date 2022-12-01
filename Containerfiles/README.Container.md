# README.Container

## podman

```bash
podman build --tag podman-django  --file Containerfile
podman run --tty --interactive --name podman-django --rm podman-django
# mount volume in development: --volume .:/code
podman exec -ti podman-django bash
```

