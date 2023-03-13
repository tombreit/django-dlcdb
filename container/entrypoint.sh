#!/bin/bash

echo "docker-entrypoint.sh"

echo "======================================================="
echo "ls -lA"
echo "$(ls -lA)"

echo "======================================================="
echo "ls -lA run/"
echo "$(ls -lA run/)"

echo "======================================================="
echo "ls -lA /opt/venv/"
echo "$(ls -lA /opt/venv/)"

echo "Prepare django app..."
# source /opt/venv/bin/activate

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput

exec "$@"
