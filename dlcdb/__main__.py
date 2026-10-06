# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The `dlcdb` command of a pip installation, equivalent to `manage.py` in a source checkout."""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dlcdb.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
