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
| `prod.txt` | `docs` | source installations without LDAP, GitLab Pages, the release workflow |
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

```bash
# set __version__ in dlcdb/__init__.py, then:
npm version X.Y.Z --no-git-tag-version  # package.json and package-lock.json
git commit --all --message "Version X.Y.Z"
git tag vX.Y.Z
git push <github-remote> main vX.Y.Z
```

The tag starts `.github/workflows/release.yml` on GitHub: it builds the
frontend assets and the docs, collects the static files, builds the wheel,
tries it in a fresh virtual environment and attaches it to a new GitHub
release. A tag that does not match both version numbers fails the workflow.
