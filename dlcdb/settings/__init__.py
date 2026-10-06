# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The settings modules: ``dlcdb.settings.base`` (manage.py, wsgi.py, python -m dlcdb)
and ``dlcdb.settings.test`` (pytest). This package imports neither, so that the test
settings can adjust the environment before ``base`` reads the ``.env``.
"""
