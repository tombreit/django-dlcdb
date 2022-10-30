#!/bin/bash

set -e
set -u


POD_NAME="pod-dlcdb"
CONTAINER_DJANGO_NAME="dlcdb-django"

podman build --tag "${CONTAINER_DJANGO_NAME}" -f Containerfile

# podman pod create --publish 8000:80 --name "${POD_DLCDB}"

podman run \
    --publish 8000:80
    --tty --interactive --rm \
    --pod "${POD_DLCDB}" \
    --name "${CONTAINER_DJANGO_NAME}" "${CONTAINER_DJANGO_NAME}"
