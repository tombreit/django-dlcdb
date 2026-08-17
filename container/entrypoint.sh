#!/bin/sh

# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: CC0-1.0

set -o errexit
#set -o nounset

INTERNAL_SERVER_PORT="${INTERNAL_SERVER_PORT:-8000}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"

echo "Run entrypoint.sh..."

# Both server modes need this. `compilemessages` is deliberately absent: the
# compiled catalog is committed and therefore already in the image.
prepare_app() {
    python3 manage.py migrate --noinput
    python3 manage.py collectstatic --noinput
}

development_server() {
    echo "Prepare django app and start development server on port ${INTERNAL_SERVER_PORT}..."
    prepare_app
    python3 manage.py runserver 0.0.0.0:"${1}"
}

production_server() {
    echo "Prepare django app and start gunicorn on port ${INTERNAL_SERVER_PORT}..."
    prepare_app
    exec gunicorn dlcdb.wsgi:application \
        --bind "0.0.0.0:${1}" \
        --workers "${GUNICORN_WORKERS}" \
        --access-logfile - \
        --error-logfile -
}

# Background tasks (huey). Run as a second container from the same image; it
# shares the database, so it must not migrate or collect static itself.
task_runner() {
    echo "Start huey task runner..."
    exec python3 manage.py run_huey
}


case "$1" in
    dev)
        development_server "${INTERNAL_SERVER_PORT}"
        ;;
    serve)
        production_server "${INTERNAL_SERVER_PORT}"
        ;;
    huey)
        task_runner
        ;;
    *)
        exec "$@"
        ;;
esac
