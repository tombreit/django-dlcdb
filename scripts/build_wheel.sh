#!/bin/bash

# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: CC0-1.0

# Builds the wheel from a commit (default HEAD) in a fresh run/release/, then
# installs it into a fresh venv and tries it the way an operator would.
#
#   scripts/build_wheel.sh [REF]
#
# Environment (both optional):
#   TAG           the release tag (the release workflow); must match the version
#   SMOKE_PYTHON  the Python for the smoke test, default python3
#
# Never builds in the working tree: setuptools leaves build/ and *.egg-info/
# behind, and the wheel needs the gitignored frontend bundles, docs and
# collected static files copied into the package.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ref=${1:-HEAD}
release_dir=$PWD/run/release
src=$release_dir/src

# Guards, against the state that gets built ($ref), not the working tree
version=$(git show "$ref:dlcdb/__init__.py" | sed -n 's/^__version__ = "\(.*\)"/\1/p')
npm_version=$(git show "$ref:package.json" | python3 -c "import json, sys; print(json.load(sys.stdin)['version'])")
if [ "$version" != "$npm_version" ]; then
    echo "dlcdb/__init__.py says $version, package.json $npm_version" >&2
    exit 1
fi
if [ -n "${TAG:-}" ] && [ "$TAG" != "v$version" ]; then
    echo "Tag $TAG does not match version $version" >&2
    exit 1
fi
if [ "$ref" = HEAD ] && ! git diff --quiet HEAD; then
    echo "Note: uncommitted changes are not part of the wheel"
fi

# Build, from the commit, outside the working tree
rm -rf "$release_dir"
mkdir -p "$src"
git archive "$ref" | tar -x -C "$src"
(
    cd "$src"
    npm ci --loglevel=error
    npm run build --loglevel=error
    make docs
    python3 manage.py collectstatic --noinput
    cp -r run/docs/html dlcdb/docs_html
    cp -r run/staticfiles dlcdb/staticfiles
    python3 -m build --wheel --outdir "$release_dir/dist"
)

# Smoke test in a fresh venv. Not from the checkout: `python -m dlcdb` there
# would import dlcdb from the checkout instead of from the wheel.
"${SMOKE_PYTHON:-python3}" -m venv "$release_dir/venv"
"$release_dir/venv/bin/pip" install --quiet "$release_dir"/dist/*.whl
mkdir "$release_dir/instance"
cd "$release_dir/instance"
DLCDB_HOME=$PWD ../venv/bin/python -m dlcdb dlcdb_init
./manage.py check
./manage.py migrate --noinput --verbosity 0
./manage.py shell --verbosity 0 --command \
    "from django.test import Client; assert Client().get('/accounts/login/', HTTP_HOST='127.0.0.1').status_code == 200"

echo "Wheel: $(ls "$release_dir"/dist/*.whl)"
