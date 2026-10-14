# Development

How the dependencies are pinned, and how a release is checked, tried and made.
Setting up a development environment is described in [Setup › Development
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

Steps 1–3 can be repeated and undone; step 4 publishes. Everything runs in the
activated dev venv, on `main`.

### 1. Check

- Everything for the release is committed, and `main` is not behind GitHub
  (`git fetch <github-remote> && git status`).
- `NEWS.md` names the significant changes.
- Optional: fresh pins with `make requirements`, committed before the checks.

```bash
ruff check . && ruff format --check .
# DATABASE_URL per command, never exported: the release build would inherit it
DATABASE_URL=sqlite://:memory: ./manage.py check
DATABASE_URL=sqlite://:memory: ./manage.py makemigrations --check --dry-run
DATABASE_URL=sqlite://:memory: pytest .
make compilemessages && git status --short  # prints nothing: the wheel ships the committed .mo
```

### 2. Build the candidate

```bash
make release VERSION=X.Y.Z
```

- writes `X.Y.Z` to `dlcdb/__init__.py`, `package.json` and `package-lock.json`
- builds `run/release/dist/dlcdb-X.Y.Z-py3-none-any.whl` from exactly that state
- smoke test: installs the wheel into a fresh `run/release/venv/` with the
  newest dependencies, sets up `run/release/instance/`, runs `check` and
  `migrate`, fetches the login page
- commits and tags nothing; refuses uncommitted changes, a malformed version
  and an existing tag

To back out, or after a fix:

```bash
git checkout -- dlcdb/__init__.py package.json package-lock.json
# fix and commit, then:
make release VERSION=X.Y.Z
```

Every build first deletes `run/release/`: stop what runs from it. `make wheel`
builds and tries `HEAD` the same way, without setting a version. The logic
lives in `scripts/prepare_release.sh` and `scripts/build_wheel.sh`.

### 3. Try the candidate

Each time, look at: logging in, the dashboard and a few lists (styled, scripts
working), the admin, the handbook at `/docs/`, the changes in `NEWS.md`. The
generated `.env` allows `127.0.0.1`, not `localhost`.

**a) Locally**, in the instance of the smoke test (runs the wheel, not the
checkout):

```bash
cd run/release/instance
./manage.py createsuperuser
./manage.py runserver 8765  # http://127.0.0.1:8765
./manage.py run_huey        # optional, in a second terminal: the task runner
```

**b) Fresh installation in a container**, the steps of [Setup › Pip
installation](setup.md#pip-installation):

```bash
podman run --rm -it --publish 8000:8000 \
    --volume ./run/release:/release:ro,Z \
    docker.io/library/debian:trixie-slim bash
```

```bash
apt-get update && apt-get install -y --no-install-recommends python3 python3-venv
useradd --home-dir /srv/dlcdb dlcdb && install -d --owner dlcdb /srv/dlcdb && su - dlcdb
python3 -m venv venv
venv/bin/pip install /release/dist/dlcdb-X.Y.Z-py3-none-any.whl
venv/bin/python -m dlcdb dlcdb_init
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver 0.0.0.0:8000  # http://127.0.0.1:8000
```

Variants:

- Python 3.12, the lowest supported version and the one the workflow tests:
  image `docker.io/library/python:3.12-slim`, without the `apt-get` line
- locked versions: `pip install … --constraint /release/src/requirements/prod.txt`
- LDAP: `apt-get install` also `libldap2-dev libsasl2-dev python3-dev gcc`,
  `pip install "/release/dist/dlcdb-X.Y.Z-py3-none-any.whl[ldap]"`

**c) Update from the last release** `vX.Y.Z`: as b), but install the last
release first:

```bash
venv/bin/pip install "dlcdb @ https://github.com/tombreit/django-dlcdb/releases/download/vX.Y.Z/dlcdb-X.Y.Z-py3-none-any.whl"
```

Create some data, then update as in [Setup › Pip
installation](setup.md#pip-installation):

```bash
venv/bin/pip install /release/dist/dlcdb-X.Y.Z-py3-none-any.whl
./manage.py dlcdb_init  # adds files that are new in this release
./manage.py migrate
./manage.py runserver 0.0.0.0:8000  # the data from before is still there
```

**d) Production data**: copy the nightly snapshot `data/db/db.sqlite3.snapshot`
([Backup](setup.md#backup)) into a directory of its own, readable for others
(the container's `dlcdb` user is not you), add
`--volume <directory>:/snapshot:ro,Z` to `podman run`, and in b) before
`migrate`:

```bash
cp /snapshot/db.sqlite3.snapshot /srv/dlcdb/data/db/db.sqlite3
```

### 4. Tag and push

```bash
git commit --all --message "Version X.Y.Z"
make wheel TAG=vX.Y.Z  # optional: the workflow's check, before the tag exists
git tag vX.Y.Z
git push <github-remote> main vX.Y.Z
```

The tag starts `.github/workflows/release.yml`: `make wheel TAG=vX.Y.Z` with
the smoke test on Python 3.12, then, only if that passed, a GitHub release with
the wheel.

Then try the published release: [Setup › Try a release](setup.md#try-a-release).

**If the workflow fails**, there is a tag but no release. For a transient
failure, rerun the workflow on GitHub. Otherwise remove the tag, fix, and start
again at step 1:

```bash
git push <github-remote> --delete vX.Y.Z
git tag --delete vX.Y.Z
```
