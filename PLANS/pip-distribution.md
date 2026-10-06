<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Pip distribution: install DLCDB from a wheel

**Status:** batch 1 done (2026-10-06). The wheel has the correct contents and a `dlcdb` command,
but an installed copy still puts `.env`, `data/` and `run/` into site-packages (batch 2). This is
a living document; each batch ticks its box in *Progress*.

## Why

Today stakeholders run DLCDB from a source checkout: clone the repo, create a venv, install
`requirements.txt`, build the frontend with npm and the docs with Sphinx. The goal is to install
it with `pip install <wheel>` instead. The wheel is self-contained: frontend bundles, `.mo` file
and built docs are included, so the target host needs neither npm nor Sphinx. Each GitHub Release
of `github.com/tombreit/django-dlcdb` carries the wheel. PyPI comes later.

Source checkouts (development, the existing Apache/mod_wsgi deployments) and the container image
keep working unchanged.

What blocks this today (seen in the leftovers of a `pip install .` in `build/lib`):
- **Wrong package layout.** `[tool.setuptools.packages.find] where = ["dlcdb"]` makes every app a
  top-level package (`accounts`, `core`, `settings`, `templates`, …). The wheel has no `dlcdb`
  package and lacks `dlcdb/urls.py` and `wsgi.py`.
- **Wrong package data.** It comes from the setuptools-scm git file finder, which ships scss
  sources and tests but none of the gitignored build output (`*/static/*/dist/`, docs HTML).
- **Instance files resolve into the package.** `.env`, `data/` and `run/` derive from
  `BASE_DIR` (`settings/base.py`). Installed, that is `site-packages/`, and the settings `mkdir`
  there on import.
- **Docs come from the checkout.** `/docs/` is served from `BASE_DIR/run/docs/html`
  (`MORE_WHITENOISE`), built from `docs/`, which is outside the package.
- **The version needs the checkout.** The footer version and repository URLs are read from
  `BASE_DIR/pyproject.toml` (`theme/context_processors.py`).
- **No CLI and no release.** There is no command-line entry point besides `manage.py`, and no
  build or release job.

`BASE_DIR / "dlcdb" / …` paths (templates, locale, static, favicon, the icon picker's
`theme.css`) are fine: inside site-packages they still point into the installed package.

## Decisions taken

1. **Distribution name `dlcdb`** (was `django-dlcdb`). The import package is already `dlcdb`, and
   `django-*` names usually mean a reusable app, not a whole site. Neither name is taken on PyPI
   (2026-10-06).
2. **GitHub Releases first, PyPI later.** A tag `vX.Y.Z` triggers a GitHub Actions workflow
   that builds the wheel and attaches it to the release. GitHub Packages has no Python registry.
   PyPI is one more job using trusted publishing, which GitHub Actions supports (self-hosted
   GitLab does not).
3. **Wheel only, pure Python (`py3-none-any`).** The sdist is not published: it could not rebuild
   the frontend anyway.
4. **Explicit package data.** Package data is listed explicitly
   (`templates/**`, `static/**`, `locale/**/*.mo`, the built docs) instead of taken from the git
   file finder. setuptools-scm is dropped; its only effect was that file finder (the version is
   static). `include-package-data` is off, so the list in `pyproject.toml` is the only source.
   Tests, frontend sources (`*/assets/`) and the `.po` file are not packaged.
   `dlcdb/conftest.py` is a module, not a package, so it is still included.
   That is harmless: only pytest imports it.
5. **Built Sphinx docs are bundled in the wheel.** `/docs/` keeps working offline and matches the
   installed version. Sphinx and its extensions move from `dependencies` to a `docs` extra. The
   requirements files include `--extra docs`, because source-checkout deployments build the docs
   on the server.
6. **The docs build goes into the package directory** (`dlcdb/docs_build/html`, gitignored)
   instead of `run/docs/html`. One path works in both modes.
7. **Instance directory `DLCDB_HOME`.** It holds `.env`, `data/` and `run/`. A source checkout
   (recognised by `pyproject.toml` next to the package) defaults to the repository root as
   before. A pip installation must set `DLCDB_HOME`, otherwise the settings raise
   `ImproperlyConfigured` with a hint.
8. **`pyproject.toml` stays the single source of the version and project URLs.** A checkout
   reads it as before. An installation reads the same values from the wheel metadata
   (`importlib.metadata`).
9. **CLI `dlcdb`** (`[project.scripts]`, `dlcdb/__main__.py`) behaves like `manage.py`:
   `dlcdb migrate`, `dlcdb run_huey`, …. `manage.py` stays for checkouts.
10. **License metadata:** SPDX expression `EUPL-1.2` (the license of the code) plus all texts from
    `LICENSES/` as license files. The table form and the license classifier are deprecated in
    setuptools ≥ 77, which is now the build requirement.

## Alternatives considered and rejected

- **`pip install git+https://…`:** the frontend bundles are not in git. The target host would
  need npm and a build step at install time.
- **GitLab package registry (gitlab.gwdg.de) or PyPI right away:** GitHub first was your call.
  PyPI follows once the wheel has proven itself.
- **Linking `/docs/` to the online docs (GitLab Pages):** that is always the latest version, not
  the installed one, and needs network access.
- **Current working directory as instance directory:** the settings create `data/` and `run/`
  on import, so any `dlcdb` call in the wrong directory would scatter them there.
- **`importlib.metadata` only:** source checkouts are not pip-installed, so the footer would lose
  its version there.

## Plan

### Batch 1: correct wheel contents (`pyproject.toml`, `Makefile`)
- `name = "dlcdb"`. In `packages.find`, use `include = ["dlcdb*"]`,
  `exclude = ["*.tests", "*.tests.*"]` and `namespaces = false`.
- Add `[tool.setuptools.package-data]`: `"*" = ["templates/**/*", "static/**/*",
  "locale/**/*.mo"]` and `"dlcdb" = ["docs_build/html/**/*"]`.
- Drop setuptools-scm from `[build-system]` and drop `[tool.setuptools_scm]`.
- Add a `docs` extra with Sphinx, pydata-sphinx-theme, sphinxcontrib-*, myst_parser,
  sphinx-design and sphinx-togglebutton.
- `Makefile requirements`: add `--extra docs` to the prod, prod-ldap, dev and container lines.
- If the build demands it, switch the license metadata to the SPDX form
  (`license = "EUPL-1.2"`, `license-files`) and drop the license classifier.
- Add `[project.scripts] dlcdb = "dlcdb.__main__:main"` and `dlcdb/__main__.py`.

### Batch 2: run outside a checkout
- `settings/base.py`: add `INSTANCE_DIR` from `DLCDB_HOME`, falling back to `BASE_DIR` for a
  checkout and raising `ImproperlyConfigured` otherwise. Derive `RUN_DIR`, `DATA_DIR` and `.env`
  from it.
- Docs build to `dlcdb/docs_build`. This touches `docs/Makefile` `BUILDDIR`, `MORE_WHITENOISE`,
  `.gitignore` and the docs copy line in `container/Containerfile`.
- `theme/context_processors.py`: if `pyproject.toml` is missing, fall back to
  `importlib.metadata.metadata("dlcdb")`.

### Batch 3: release workflow and docs
- Add `.github/workflows/release.yml`, triggered on a `v*` tag push:
  1. `npm ci` and `npm run build`
  2. `pip install -r requirements/prod.txt build` and `make docs`
  3. check that the tag matches the `pyproject.toml` version
  4. `python -m build --wheel`
  5. smoke test in a fresh venv: `dlcdb check`, `dlcdb migrate`
  6. `gh release create`
- `docs/betrieb/setup.md`: add a section "Installation via pip". It covers:
  - the wheel URL with extras
  - optional constraints from `requirements/prod.txt` of the same tag
  - `DLCDB_HOME`
  - systemd for huey
  - a `wsgi.py` stub for Apache/mod_wsgi
- `NEWS.md`: one line.

## Open follow-ups

- **Release version.** `pyproject.toml` says 0.9.3, `package.json` 2.0.1 and
  `SPECTACULAR_SETTINGS["VERSION"]` 2.0.0. Pick one before the first tag.
- **`Django==6.1.1` exact pin.** Pip users only get Django security releases with a new DLCDB
  release. Consider `Django>=6.1.1,<6.2`.
- **PyPI.** Add a publish job with trusted publishing to the release workflow.
- **`createcachetable`.** The `select2` DatabaseCache table `dlcdb_select2` is never created
  (not documented, not in `container/entrypoint.sh`). This is independent of this plan.

## Pitfalls

- Package data globs match whatever is on disk. Build the wheel only after `npm run build` and
  `make docs`, otherwise it silently lacks bundles or docs.
- setuptools reuses `build/lib/`. Delete `build/` (it holds the old top-level layout) and
  `dlcdb/*.egg-info` before building locally, or stale packages end up in the wheel.
- `DLCDB_HOME` cannot be set in `.env`, because it is what locates `.env`.
- mod_wsgi does not pass Apache `SetEnv` into `os.environ`. That is why a pip installation behind
  Apache needs the `wsgi.py` stub that sets `DLCDB_HOME`.

## Progress

- [x] Batch 0: this document
- [x] Batch 1: correct wheel contents
- [ ] Batch 2: run outside a checkout
- [ ] Batch 3: release workflow and docs
