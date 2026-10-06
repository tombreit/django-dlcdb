# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
`python -m dlcdb`: Django's command-line utility for a pip installation, like
`manage.py` in a source checkout. The `manage.py` that `dlcdb_init` writes into
an instance directory calls `main()` as well.
"""

import os
import sys


def main(argv=None):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dlcdb.settings.base")

    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)


if __name__ == "__main__":
    # Otherwise Django calls itself "python -m django" in its help texts
    main(["python -m dlcdb", *sys.argv[1:]])
