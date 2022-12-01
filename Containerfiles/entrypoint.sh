#!/bin/bash

echo "docker-entrypoint.sh"

echo "$(ls -lA)"
echo "$(ls -lA run/)"
echo "$(ls -lA /opt/venv/)"

#echo "$(tree -a /app/)"

echo "Prepare django app..."
# source /opt/venv/bin/activate

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput

exec "$@"
