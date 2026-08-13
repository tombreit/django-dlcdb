<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# django-dlcdb

Device Lifecycle Database

## Tech Stack

- Target OS: Debian 13 Trixie or newer
- Python 3.13+
- Django 6+

## Entrypoints

- Django managements commands: `./manage.py`
- Bundle static assets: `npm run build`
- Python test suite: pytest `pytest .`
- Generate updated requirements from pyroject.toml: `make requirements`

## Notes

- No raw SQL, but keep an eye on queryset optimiziations like `prefetch_related`, `select_related` etc.
- Use native Django and Python idioms where possible
- If possible, do not introduce custom Django template tags
- Write the code for human inspection, favour readability
- If in doubt: ask me
- You may suggest commit messages, but do not commit on your own
- If adding SPDX license headers: omit the year
- Do not run `manage.py makemessages` and do not modify the po translation files. I will take care of the translation stuff. Just ensure that the user facing strings in the codebase are marked as "translateable".

## Quirks

- Django template language supports only single line comments via `{# ... #}`, multiline comments via `{% comment %}...{% endcomment %}`
