# Development

How the dependencies are pinned and how a release is made. Setting up a
development environment is described in [Setup › Development
setup](setup.md#development-setup).

## Dependencies and lock files

`pyproject.toml` lists the direct dependencies, mostly without versions (Django
is pinned exactly), and the extras `docs`, `ldap`, `container` and `dev`. A
wheel declares exactly these, so `pip install dlcdb` takes the newest matching
versions.

The files in `requirements/` are the lock files: pip-compile (pip-tools) pins
every package, including the indirect ones, for one combination of extras:

| File | Extras | Used by |
|---|---|---|
| `prod.txt` | `docs` | source installations without LDAP, GitHub Pages, the release workflow |
| `prod-ldap.txt` | `docs`, `ldap` | source installations with LDAP (`requirements.txt` links here) |
| `dev.txt` | `docs`, `dev` | development |
| `container.txt` | `docs`, `ldap`, `container` | the container image |

`make requirements` compiles all four and **upgrades every pin**. To add or
remove a dependency without upgrading anything else, run the pip-compile
commands of the `Makefile` without `--upgrade`: pip-compile then keeps the
existing pins.

A pip installation does not see these files. To install a release with exactly
its locked versions, for example when a newer dependency breaks something, add
them as constraints (`prod.txt` without LDAP):

```bash
pip install "dlcdb[ldap] @ https://github.com/tombreit/django-dlcdb/releases/download/vX.Y.Z/dlcdb-X.Y.Z-py3-none-any.whl" \
    --constraint https://raw.githubusercontent.com/tombreit/django-dlcdb/vX.Y.Z/requirements/prod-ldap.txt
```

The static files in the wheel were collected with these versions, too.

[PEP 751](https://peps.python.org/pep-0751/) defines `pylock.toml` as the
standard lock file format. pip can write and install it (`pip lock`,
`pip install -r pylock.toml`), but marks both as experimental (pip 26.2); until
that changes, the project stays with pip-compile.

## Release

In the activated dev venv:

```bash
make release VERSION=X.Y.Z
git commit --all --message "Version X.Y.Z"
git tag vX.Y.Z
git push <github-remote> main vX.Y.Z
```

`make release` refuses to run with uncommitted changes, with a version not of
the form `X.Y.Z`, or when the tag exists already. It writes the version to
`dlcdb/__init__.py`, `package.json` and `package-lock.json`, then builds the
wheel from exactly the state you are about to commit and tries it in a fresh
virtual environment (`make wheel`). Everything it builds stays in
`run/release/`, outside the working tree. The logic lives in
`scripts/prepare_release.sh` and `scripts/build_wheel.sh`; the `Makefile` only
calls them.

`make wheel` alone builds and tries a release candidate from `HEAD`; the wheel
lands in `run/release/dist/`.

The pushed tag starts `.github/workflows/release.yml` on GitHub. It runs
`make wheel` on the tag, with the smoke test on Python 3.12, and attaches the
wheel to a new GitHub release. A tag that does not match both version numbers
fails the workflow.

## Trying a wheel in a container

To try a wheel before it is released, install it into a fresh container, the
way an operator installs a release:

```bash
make wheel  # builds run/release/dist/dlcdb-X.Y.Z-py3-none-any.whl from HEAD
podman run --rm -it --publish 8000:8000 \
    --volume ./run/release/dist:/wheels:ro,Z \
    docker.io/library/debian:trixie-slim bash
```

In the container, follow [Setup › Pip installation](setup.md#pip-installation),
with the wheel file instead of the release URL:

```bash
apt-get update && apt-get install -y --no-install-recommends python3 python3-venv
useradd --create-home --home-dir /srv/dlcdb dlcdb && su - dlcdb
python3 -m venv /srv/dlcdb/venv
/srv/dlcdb/venv/bin/pip install /wheels/dlcdb-*.whl
DLCDB_HOME=/srv/dlcdb /srv/dlcdb/venv/bin/python -m dlcdb dlcdb_init
cd /srv/dlcdb
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver 0.0.0.0:8000
```

Then open <http://127.0.0.1:8000>. The generated `.env` allows `127.0.0.1`,
not `localhost`. For Python 3.12, the lowest supported version, use
`docker.io/library/python:3.12-slim` instead and skip the `apt-get` line.
`--rm` discards the container on exit.
