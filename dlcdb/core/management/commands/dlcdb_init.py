# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Create the files of this DLCDB instance in its instance directory: ``.env`` with
a fresh secret key, and for a pip installation (``DLCDB_HOME``) also a short
``README.md``, a ``manage.py`` and a ``wsgi.py`` that run DLCDB for that
directory. A source checkout brings its own README, manage.py and dlcdb/wsgi.py.

Existing files are never touched, so the command is safe to run again; after an
update it only adds files that are new.

    DLCDB_HOME=/srv/dlcdb /srv/dlcdb/venv/bin/python -m dlcdb dlcdb_init
    ./manage.py dlcdb_init
"""

import secrets
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

import dlcdb

# Template, file name in the instance directory, file mode, note
FILES = [
    # The mode keeps the secret key from other users
    ("core/init/env.template", ".env", 0o600, " (edit it before the first start)"),
]
PIP_INSTALLATION_FILES = [
    ("core/init/README.md", "README.md", 0o644, ""),
    ("core/init/manage.py.template", "manage.py", 0o755, ""),
    ("core/init/wsgi.py.template", "wsgi.py", 0o644, ""),
]


class Command(BaseCommand):
    help = (
        "Create .env (with a fresh secret key) in the instance directory, for a pip installation also "
        "README.md, manage.py and wsgi.py; existing files stay untouched."
    )

    def handle(self, *args, **options):
        context = {
            # URL-safe: `$` and `#` have a meaning in django-environ .env files
            "secret_key": secrets.token_urlsafe(50),
            # The Python of this installation's venv, for the shebang of manage.py
            "python": sys.executable,
            "version": dlcdb.__version__,
        }
        files = FILES if settings.SOURCE_CHECKOUT else FILES + PIP_INSTALLATION_FILES
        for template, name, mode, note in files:
            path = settings.INSTANCE_DIR / name
            # Rendered first: a failing template must not leave an empty file
            # behind, which every later run would skip as existing.
            content = render_to_string(template, context)
            try:
                # Created empty with its final mode, never over an existing file
                path.touch(mode=mode, exist_ok=False)
            except FileExistsError:
                self.stdout.write(f"Skipped {path} (exists)")
                continue
            try:
                path.write_text(content)
            except OSError:
                path.unlink()  # same reason: no half-written file
                raise
            self.stdout.write(self.style.SUCCESS(f"Created {path}{note}"))
