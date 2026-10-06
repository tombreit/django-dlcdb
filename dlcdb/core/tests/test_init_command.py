# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import io
import re
import stat

from django.core.management import call_command


def test_init_creates_env_and_readme_once(settings, tmp_path):
    settings.INSTANCE_DIR = tmp_path

    call_command("init", stdout=io.StringIO())

    env_file = tmp_path / ".env"
    env = env_file.read_text()
    assert re.search(r"^SECRET_KEY=[A-Za-z0-9_-]{60,}$", env, re.MULTILINE)
    assert "{{" not in env
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert f"export DLCDB_HOME={tmp_path}" in (tmp_path / "README.md").read_text()

    # A second run keeps both files as they are
    out = io.StringIO()
    call_command("init", stdout=out)
    assert env_file.read_text() == env
    assert out.getvalue().count("Skipped") == 2
