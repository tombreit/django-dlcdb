#!/bin/sh

echo "docker-entrypoint.sh"

echo "$(ls -lA)"
echo "$(tree -a run/)"

# echo "Prepare static assets via npm build scripts..."
# npm install
# npm run prod

echo "Prepare django app..."
source /path/to/dlcdb/venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

echo "Prepare sphinx docs..."
cd ./docs/
make html
cd ../

exec "$@"
