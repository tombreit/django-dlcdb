<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# django-dlcdb

Device Lifecycle Database

## Tech Stack

- Target OS: Debian 13 Trixie or newer
- Python 3.12+
- Django 6+

## Entrypoints

- Django managements commands: `./manage.py`
- Bundle static assets: `npm run build`
- Python test suite: pytest `pytest .`
- Generate updated requirements from pyroject.toml: `make requirements`
- Checks: `ruff check . && ruff format --check .`; `./manage.py check`; `./manage.py makemigrations --check --dry-run`; `pytest .`

## Notes

- No raw SQL, but keep an eye on queryset optimiziations like `prefetch_related`, `select_related` etc.
- Use native Django and Python idioms where possible
- If possible, do not introduce custom Django template tags
- Write the code for human inspection, favour readability
- If in doubt: ask me
- `dlcdb/core` is the contract the other apps rely on; its rules are the module docstring of `dlcdb/core/__init__.py`. Read it before changing core or how an app uses it
- `PLANS/` holds living design documents for work that is planned but not yet implemented
- You may suggest commit messages, but do not commit on your own
- If adding SPDX license headers: omit the year
- Do not run `manage.py makemessages` and do not modify the po translation files. I will take care of the translation stuff. Just ensure that the user facing strings in the codebase are marked as "translateable".
- Add a `NEWS.md` entry for every significant change, not for every commit or fix
- Never use the dev database for checks or experiments: `DATABASE_URL=sqlite://:memory:`

## Architecture

- `core` imports no other app (its docstring names the one exception); every app may import `core`. Foreign keys to another app's model are strings (`"tenants.Tenant"`)
- Locality of behaviour: code lives in the app whose screens or workflows use it; `core` keeps only what several apps share (models, lifecycle, shared rules)
  - a workflow is a module named after the action (`dataexchange/importer.py`, `inventory/inventorize.py`); no `services.py` layer
  - an app plugs into shared UI from its own code: `navigation.py` for the navbar, `theme.pickers.register_picker_source` in `AppConfig.ready()` for device pickers
- The Django admin is being phased out: new UI goes into the frontend apps, not the admin
- Presentation (CSS classes, labels, per-screen URLs) lives in templates or `theme`, not in core models; models return data
- Shared UI helpers live in `theme` (filterbar, pagination, pickers, device state buttons); reuse them
- No Django signals: call explicitly (journal entries, notifications). If really needed: let me know.
- Tenant scoping: every view that loads an object by pk or uuid goes through `tenant_scoped_queryset`; on a multi-valued relation keep the tenant condition in the same `filter()` as the others

## Quirks

- Django template language supports only single line comments via `{# ... #}`, multiline comments via `{% comment %}...{% endcomment %}`
- Today's date is `timezone.localdate()`; `timezone.now().date()` is the UTC date
- Stored dates have no upper bound (9999-12-31 occurs): don't add days to them
- A `ModelAdmin` instance is shared by all requests: never keep request state on `self`
- Lifecycle `transition_*` functions check state, not permissions; views check permissions (`lifecycle.available`)
- Warnings fail the test suite: close files (`with ….open()`), use aware datetimes
- Before moving or deleting a template, template tag or method, grep `.html`, `.txt` (mail templates) and the migrations: DB-stored lending templates load `markdown_extras` by name
