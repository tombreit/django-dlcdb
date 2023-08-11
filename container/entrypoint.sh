#!/bin/sh

set -o errexit
set -o nounset

echo "Run entrypoint.sh..."

echo "Prepare django app..."
python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8000

exec "$@"
