<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Pip distribution: install DLCDB from a wheel

**Status:** batches 0–7 done (2026-10-06); batch 8 (`init` writes `manage.py` and
`wsgi.py`) comes before the first tag. A pushed `vX.Y.Z` tag builds the wheel on GitHub
and attaches it to a release. The wheel ships the collected static files, so a pip
installation needs no `collectstatic`, and `dlcdb init` writes the instance's `.env` (with a
fresh secret key) and a README. `docs/betrieb/setup.md` describes installation, production use
and updates. `docs/betrieb/development.md` covers dependencies, lock files and releasing.
Installations without the `ldap` extra work since the LDAP backend moved into its own module
(`accounts/ldap_backends.py`). No release has been tagged yet (see *Open follow-ups*). This is
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
6. **Generated files stay in `run/`, the working tree stays clean.** `make docs` keeps writing
   to `run/docs`. Only the wheel build copies `run/docs/html` into the package
   (`dlcdb/docs_html`), and it does so on CI or in a scratch copy. setuptools always writes
   `build/` and `*.egg-info/` into the project root, and pyproject offers no option to move them.
   So wheels are never built in the working tree. `settings.DOCS_DIR` picks the docs location
   via `SOURCE_CHECKOUT`.
7. **Instance directory `DLCDB_HOME`.** It holds `.env` and `data/`. A source checkout
   (recognised by `pyproject.toml` next to the package) always uses the repository root and
   ignores `DLCDB_HOME`, so an exported `DLCDB_HOME` cannot redirect a dev checkout to a
   production instance (since batch 7). A pip installation must set `DLCDB_HOME`, otherwise
   the settings raise `ImproperlyConfigured` with a hint.
8. **The version lives in code: `dlcdb.__version__`.** It is the single source.
   `pyproject.toml` takes it via `dynamic = ["version"]`, and the footer imports it. Checkouts,
   the container and wheels see the same value without reading any file at runtime. The API
   schema (`SPECTACULAR_SETTINGS["VERSION"]`) uses it too. `package.json` and
   `package-lock.json` cannot import it, so they carry the same number by hand. They were
   consolidated to 0.9.4 in batch 2; before that, 0.9.3, 2.0.1 and 2.0.0 were in use. You bump
   it by hand before tagging; the release workflow checks that the tag matches. The footer's
   repository and issues URLs are constants in `theme/context_processors.py`, kept in step with
   `[project.urls]`, which can't be dynamic.
9. **CLI `dlcdb`** (`[project.scripts]`, `dlcdb/__main__.py`) behaves like `manage.py`:
   `dlcdb migrate`, `dlcdb run_huey`, …. `manage.py` stays for checkouts.
10. **License metadata:** SPDX expression `EUPL-1.2` (the license of the code) plus all texts from
    `LICENSES/` as license files. The table form and the license classifier are deprecated in
    setuptools ≥ 77, which is now the build requirement.
11. **The wheel ships the collected static files.** DLCDB has no instance-specific static files
    (branding uploads are media), so the release build runs `collectstatic` once and copies
    `run/staticfiles` into the package (`dlcdb/staticfiles`). In a wheel, `STATIC_ROOT` points
    there (`settings.STATICFILES_DIR` via `SOURCE_CHECKOUT`). Install and update need no
    `collectstatic`, and the static files always match the installed release. The collected
    files reflect the dependency versions of the release build. So the three third-party
    packages that contribute to them, Django (admin), `djangorestframework` and `django-htmx`,
    are pinned exactly in `pyproject.toml`; a newer version could reference static files the
    wheel lacks. (Batch 4 tried `WHITENOISE_MANIFEST_STRICT = False` instead. It does not help:
    Django still raises for a file missing from `STATIC_ROOT`. Removed in batch 7.) The cost is
    a larger wheel.

## Alternatives considered and rejected

- **`pip install git+https://…`:** the frontend bundles are not in git. The target host would
  need npm and a build step at install time.
- **GitLab package registry (gitlab.gwdg.de) or PyPI right away:** GitHub first was your call.
  PyPI follows once the wheel has proven itself.
- **Linking `/docs/` to the online docs (GitLab Pages):** that is always the latest version, not
  the installed one, and needs network access.
- **Current working directory as instance directory:** the settings create `data/` and `run/`
  on import, so any `dlcdb` call in the wrong directory would scatter them there.
- **Reading the version at runtime** (`pyproject.toml` in a checkout, `importlib.metadata` in a
  wheel): two code paths, file IO and error handling for three footer strings. It was tried in
  batch 2 and replaced by `dlcdb.__version__`.
- **Version from the git tag (setuptools-scm `version_file`):** that file only exists after a
  build. Source checkouts, including the Apache deployments, would lose the footer version.
- **Building the docs straight into the package directory** (one path for both modes): this
  puts build output and the Sphinx doctrees cache into `dlcdb/`. It was tried in batch 2 and
  reverted.

## Plan

### Batch 1: correct wheel contents (`pyproject.toml`, `Makefile`)
- `name = "dlcdb"`. In `packages.find`, use `include = ["dlcdb*"]`,
  `exclude = ["*.tests", "*.tests.*"]` and `namespaces = false`.
- Add `[tool.setuptools.package-data]`: `"*" = ["templates/**/*", "static/**/*",
  "locale/**/*.mo"]` and the docs entry (`"dlcdb" = ["docs_html/**/*"]` since batch 2).
- Drop setuptools-scm from `[build-system]` and drop `[tool.setuptools_scm]`.
- Add a `docs` extra with Sphinx, pydata-sphinx-theme, sphinxcontrib-*, myst_parser,
  sphinx-design and sphinx-togglebutton.
- `Makefile requirements`: add `--extra docs` to the prod, prod-ldap, dev and container lines.
- If the build demands it, switch the license metadata to the SPDX form
  (`license = "EUPL-1.2"`, `license-files`) and drop the license classifier.
- Add `[project.scripts] dlcdb = "dlcdb.__main__:main"` and `dlcdb/__main__.py`.

### Batch 2: run outside a checkout
- `settings/base.py`: add `SOURCE_CHECKOUT` (`pyproject.toml` next to the package). Add
  `INSTANCE_DIR` from `DLCDB_HOME`, falling back to `BASE_DIR` for a checkout and raising
  `ImproperlyConfigured` otherwise. Derive `RUN_DIR`, `DATA_DIR` and `.env` from it.
- `settings/base.py`: `DOCS_DIR` is `run/docs/html` in a checkout and `dlcdb/docs_html` in a
  wheel. `MORE_WHITENOISE` serves it.
- `pyproject.toml`: the package-data entry and its comment point to `dlcdb/docs_html`.
- `dlcdb/__init__.py`: `__version__`. `pyproject.toml`: `dynamic = ["version"]` from
  `dlcdb.__version__`. `theme/context_processors.py` imports it, and the URLs become constants.
- Versions consolidated to 0.9.4: `dlcdb.__version__`, `package.json` and `package-lock.json`.
  The API schema version comes from `dlcdb.__version__`.

### Batch 3: release workflow and docs
- Add `.github/workflows/release.yml`, triggered on a `v*` tag push. It uses only the
  checkout/setup-node/setup-python actions (v7), Node 24 and Python 3.13:
  1. check that the tag matches `dlcdb.__version__` and the `package.json` version
  2. `npm ci` and `npm run build`
  3. `pip install -r requirements/prod.txt build`, `make docs`, then
     `cp -r run/docs/html dlcdb/docs_html`
  4. `python -m build --wheel`
  5. smoke test in a fresh venv: `dlcdb check`, `dlcdb migrate`, `dlcdb collectstatic`
  6. `gh release create … --generate-notes` with the wheel
  No system packages: libmagic is not needed (`python-magic` was unused and has been removed).
- `docs/betrieb/setup.md`: a new section *Pip installation*, plus *Operations › Release*. The
  section covers:
  - install, including the wheel URL with extras and optional constraints from the
    `requirements/` of the same tag
  - `DLCDB_HOME`
  - the systemd `[Service]` section for the task runner
  - the `wsgi.py` stub for Apache/mod_wsgi
  - updates

  *Operations › Release* covers the version bump with `npm version X.Y.Z --no-git-tag-version`
  for the npm files, and the tag push. The introduction names all three ways to run DLCDB.
- `NEWS.md`: one line.

### Batch 4: collected static files ship in the wheel
- `settings/base.py`: `STATICFILES_DIR` (= `STATIC_ROOT`) is `run/staticfiles` in a checkout
  and `dlcdb/staticfiles` in a wheel. `WHITENOISE_MANIFEST_STRICT = SOURCE_CHECKOUT`.
- `pyproject.toml` package-data: `staticfiles/**/*` for `dlcdb`.
- `release.yml`: `collectstatic` and `cp -r run/staticfiles dlcdb/staticfiles` before the wheel
  build. The smoke test checks for `staticfiles.json` in the installed package and requests the
  login page, instead of running `collectstatic`.
- `setup.md` *Pip installation*: no `collectstatic` in *Install* and *Update*; the instance
  directory holds `.env` and `data/`.

### Batch 5: `dlcdb init`
- A management command `init` creates the starting files of an instance directory from
  templates shipped in the package. It never overwrites anything, so it is safe to run again,
  and after an update it only adds what is new:
  - `.env`, from `env.template` (moved into `core/templates/core/init/`), with a fresh
    `SECRET_KEY`. The key comes from `secrets.token_urlsafe`, because `$` and `#` mean something
    in django-environ files, and the file gets mode 0600.
  - a short `README.md` with links to the docs

  The templates get their license from a `REUSE.toml` annotation, so the generated files carry
  no SPDX headers.
- The template now defaults to `DJANGO_DEBUG=false`, with a hint that `true` needs the dev
  requirements. With `true`, the settings load the debug toolbar and django-extensions. A pip
  installation doesn't have them, so every `dlcdb` command after `init` crashed until the line
  was edited.
- The name follows `git init` / `cargo init` / `sentry init`. `doctor` was rejected because it
  diagnoses instead of creating (that belongs in Django's system checks). `bootstrap` was
  rejected as vague, and because it collides with the Bootstrap CSS framework.
- Docs: `dlcdb init` replaces the curl line, and `./manage.py init` replaces
  `cp env.template .env`. `management_commands.md` gets an entry, and `NEWS.md` a line.

### Batch 6: developer page
- New `docs/betrieb/development.md` with *Dependencies and lock files*:
  - the roles of `pyproject.toml` and `requirements/*.txt`
  - `make requirements` versus pip-compile without `--upgrade`
  - the `--constraint` hint for pip installations
  - `pylock.toml` as the future option

  It also gets *Release*, moved from `setup.md`. `setup.md` keeps only what operators need: the
  constraints paragraph and *Operations › Requirements* are gone, and *Development setup* links
  to the new page.
- `setup.md` *Development setup*: "edit .env, for development set `DJANGO_DEBUG=true`". Since
  batch 5, `init` writes `false`. Without `DEBUG` and without `collectstatic`, the strict
  manifest would fail the dev server's pages.

### Batch 7: fixes from the review of the branch
- Pin `djangorestframework==3.18.1` and `django-htmx==1.29.0` exactly, like Django (decision 11).
  Remove the ineffective `WHITENOISE_MANIFEST_STRICT` line.
- `init` creates each file empty with its final mode via `Path.touch(mode=…, exist_ok=False)`
  (internally `os.open` with `O_CREAT | O_EXCL`), then writes the content. Before,
  `.env` was readable by other users for a moment (written with the umask, then `chmod 0600`),
  and two concurrent runs could overwrite each other.
- The `env.template` banner no longer claims that a missing `.env` means development mode. It
  means the publicly known fallback `SECRET_KEY`.
- Python 3.12 stays the minimum (`67f37831`). `setup.md`, `README.md` and `AGENTS.md` now say
  3.12+, and the release workflow smoke-tests the wheel on 3.12 while building on 3.13.
- `DLCDB_HOME` only applies to pip installations (decision 7).
- The README quickstart runs `manage.py init` and says to set `DJANGO_DEBUG=true`. Without a
  `.env`, `DEBUG` is off and the dev server fails without `collectstatic`.

### Batch 8: `init` writes `manage.py` and `wsgi.py`
- Django users feel at home in a pip installation: `dlcdb init` additionally writes into
  `DLCDB_HOME` a `manage.py` and the Apache `wsgi.py`. `manage.py` gets a shebang to the venv's
  Python, and both set `DLCDB_HOME` to their own directory. Operators then run
  `cd /srv/dlcdb && ./manage.py migrate` without exporting `DLCDB_HOME`, and nobody writes the
  wsgi stub by hand. `dlcdb` is left for `init` and DLCDB-specific commands. The docs
  (pip *Install*, *Production*, *Update*, the instance README) switch to `./manage.py`.

## Open follow-ups

- **PyPI.** Add a publish job with trusted publishing to the release workflow.
- **`createcachetable`: resolved by removing django-select2.** No widget had used it since
  2023, so its DatabaseCache table `dlcdb_select2` is not needed. Old installations may keep the
  empty table; it is harmless.
- **`python-magic`: removed.** Its only use, a CSV MIME check in the bulk decommissioning
  import, went away in March 2025 (`a84fba15`). The container and GitLab CI no longer install
  libmagic.
- **First release.** After batch 8: tag `v0.9.4` and push the tag to GitHub. Check the workflow
  run and the release page, then try the documented install from the release URL. Neither
  Python 3.12 nor the upload has been tried locally.
- **Left open from the branch review:**
  - The wheel ships each app's raw `static/**` as well as the collected copies, about 6 MB
    extra. The raw ones are only needed by the favicon view and the icon picker
    (`theme/bootstrap_icons.py`).
  - The project URLs (footer, wheel metadata) point to GitLab, while releases are on GitHub.
  - `cp -r` into an existing target nests the copy. Fresh CI runners are unaffected; repeated
    local builds in the same scratch copy are not.
  - `npm ci` reports `npm audit` advisories in the frontend dependencies.

## Pitfalls

- Package data globs match whatever is on disk. Build the wheel only after `npm run build`,
  `make docs`, `collectstatic` and the copies to `dlcdb/docs_html` and `dlcdb/staticfiles`.
  Otherwise it silently lacks bundles, docs or static files.
- Collect the static files with the production requirements and without a `.env` that turns
  on `DEBUG`. Otherwise dev-only apps (debug toolbar, django-extensions) end up in the wheel.
- Build wheels only on CI or in a scratch copy (`git ls-files` plus the three `dist/` bundles
  plus `dlcdb/docs_html` and `dlcdb/staticfiles`). In the working tree, setuptools leaves
  `build/` and `dlcdb.egg-info/` behind and reuses a stale `build/lib/` on the next build.
- `DLCDB_HOME` cannot be set in `.env`, because it is what locates `.env`.
- mod_wsgi does not pass Apache `SetEnv` into `os.environ`. That is why a pip installation behind
  Apache needs the `wsgi.py` stub that sets `DLCDB_HOME`.

## Progress

- [x] Batch 0: this document
- [x] Batch 1: correct wheel contents
- [x] Batch 2: run outside a checkout
- [x] Batch 3: release workflow and docs
- [x] Batch 4: collected static files ship in the wheel
- [x] Batch 5: `dlcdb init`
- [x] Batch 6: developer page
- [x] Batch 7: fixes from the review of the branch
- [ ] Batch 8: `init` writes `manage.py` and `wsgi.py`
