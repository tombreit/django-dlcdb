#!/usr/bin/env python

# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: CC0-1.0

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dlcdb.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
