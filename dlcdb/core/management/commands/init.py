# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Create the starting files of this DLCDB instance in its instance directory
(``DLCDB_HOME`` of a pip installation, the repository root of a source checkout):
``.env`` with a fresh secret key, and a short ``README.md``.

Existing files are never touched, so the command is safe to run again; after an
update it only adds files that are new.

    dlcdb init
    python manage.py init
"""

import secrets

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

import dlcdb

# Template, file name in the instance directory, file mode (.env holds the secret key), note
FILES = [
    ("core/init/env.template", ".env", 0o600, " (edit it before the first start)"),
    ("core/init/README.md", "README.md", 0o644, ""),
]


class Command(BaseCommand):
    help = "Create .env (with a fresh secret key) and README.md in the instance directory, unless they exist."

    def handle(self, *args, **options):
        context = {
            # URL-safe: `$` and `#` have a meaning in django-environ .env files
            "secret_key": secrets.token_urlsafe(50),
            "instance_dir": settings.INSTANCE_DIR,
            "version": dlcdb.__version__,
        }
        for template, name, mode, note in FILES:
            path = settings.INSTANCE_DIR / name
            try:
                # Created empty with its final mode, never over an existing file
                path.touch(mode=mode, exist_ok=False)
            except FileExistsError:
                self.stdout.write(f"Skipped {path} (exists)")
                continue
            path.write_text(render_to_string(template, context))
            self.stdout.write(self.style.SUCCESS(f"Created {path}{note}"))
