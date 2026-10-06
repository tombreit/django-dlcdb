# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from huey import MemoryHuey

from .base import *

# Tests assert English UI strings; keep rendering language-independent.
LANGUAGE_CODE = "en"

# PBKDF2 costs ~0.2 s per password by design; tests need no strong hashes.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Each test client builds its middleware anew, and WhiteNoise would then scan
# all static files every time. Autorefresh looks a file up per request instead.
WHITENOISE_AUTOREFRESH = True

# Tasks enqueued by tests stay in memory instead of the instance's queue file.
HUEY = MemoryHuey(name="dlcdb_huey", results=False)
