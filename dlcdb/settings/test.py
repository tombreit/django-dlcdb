# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import os

from huey import MemoryHuey

# Test the production settings, even if the developer's .env sets
# DJANGO_DEBUG=true (debug toolbar, dev apps): base reads the .env without
# overriding variables that are already set.
os.environ["DJANGO_DEBUG"] = "false"

from .base import *

# Tests assert English UI strings; keep rendering language-independent.
LANGUAGE_CODE = "en"

# Unlike production, a broken form layout should fail the test.
CRISPY_FAIL_SILENTLY = False

# PBKDF2 costs ~0.2 s per password by design; tests need no strong hashes.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Each test client builds its middleware anew, and WhiteNoise would then scan
# all static files every time. Autorefresh looks a file up per request instead.
WHITENOISE_AUTOREFRESH = True

# Rendering needs no built static files: the manifest storage needs collectstatic.
# theme/tests/test_static_references.py checks the templates' static paths instead.
STORAGES = {**STORAGES, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}

# Tasks enqueued by tests stay in memory instead of the instance's queue file.
HUEY = MemoryHuey(name="dlcdb_huey", results=False)
