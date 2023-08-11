#!/bin/sh

set -o errexit
#set -o nounset

INTERNAL_SERVER_PORT="${INTERNAL_SERVER_PORT:-8000}"

echo "Run entrypoint.sh..."

development_server() {
    echo "Prepare django app and start development server on port ${INTERNAL_SERVER_PORT}..."
    python3 manage.py migrate --noinput
    python3 manage.py collectstatic --noinput
    python manage.py runserver 0.0.0.0:${1}
}


case "$1" in
    dev)
        development_server "${INTERNAL_SERVER_PORT}"
        ;;
    *)
        exec "$@"
        ;;
esac
