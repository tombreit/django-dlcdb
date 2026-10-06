#!/bin/bash

# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: CC0-1.0

# Prepares release X.Y.Z: writes the version to dlcdb/__init__.py, package.json
# and package-lock.json, then builds and tries the wheel from exactly that
# state. Commit, tag and push stay yours.
#
#   scripts/prepare_release.sh X.Y.Z
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

version=${1:-}

# Guards
if ! [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Usage: scripts/prepare_release.sh X.Y.Z (or: make release VERSION=X.Y.Z)" >&2
    exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
    echo "Commit or stash your changes first: a release is the committed state" >&2
    exit 1
fi
if git rev-parse --quiet --verify "refs/tags/v$version" > /dev/null; then
    echo "Tag v$version exists already" >&2
    exit 1
fi

# The version, in all three places
sed -i "s/^__version__ = \".*\"/__version__ = \"$version\"/" dlcdb/__init__.py
npm version "$version" --no-git-tag-version --allow-same-version --loglevel=error > /dev/null

# The wheel, from the committed tree plus the version change. `git stash
# create` turns that state into a commit object without touching the branch or
# the stash list. If the version was already set, HEAD is that state; `git stash
# create` would fail there, because npm rewrote the files with the same content.
if git diff --quiet; then
    ref=HEAD
else
    ref=$(git stash create)
fi
scripts/build_wheel.sh "$ref"

if ! git diff --quiet; then
    echo "Next: git commit --all --message \"Version $version\""
fi
echo "Then: git tag v$version && git push <github-remote> HEAD v$version"
