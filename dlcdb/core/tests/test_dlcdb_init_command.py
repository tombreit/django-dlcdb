# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import io
import os
import re
import stat
import sys

import pytest
from django.core.management import call_command
from django.template import TemplateDoesNotExist


def test_dlcdb_init_creates_the_files_of_a_pip_installation_once(settings, tmp_path):
    settings.INSTANCE_DIR = tmp_path
    settings.SOURCE_CHECKOUT = False

    call_command("dlcdb_init", stdout=io.StringIO())

    assert sorted(path.name for path in tmp_path.iterdir()) == [".env", "README.md", "manage.py", "wsgi.py"]
    env_file = tmp_path / ".env"
    env = env_file.read_text()
    assert re.search(r"^SECRET_KEY=[A-Za-z0-9_-]{60,}$", env, re.MULTILINE)
    assert "{{" not in env
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    manage_py = tmp_path / "manage.py"
    assert manage_py.read_text().startswith(f"#!{sys.executable}\n")
    assert os.access(manage_py, os.X_OK)

    # A second run keeps all files as they are
    out = io.StringIO()
    call_command("dlcdb_init", stdout=out)
    assert env_file.read_text() == env
    assert out.getvalue().count("Skipped") == 4


def test_dlcdb_init_in_a_source_checkout_creates_only_env(settings, tmp_path):
    settings.INSTANCE_DIR = tmp_path
    settings.SOURCE_CHECKOUT = True

    call_command("dlcdb_init", stdout=io.StringIO())

    assert [path.name for path in tmp_path.iterdir()] == [".env"]


def test_dlcdb_init_leaves_no_empty_file_when_rendering_fails(settings, tmp_path, monkeypatch):
    """Otherwise a later run would skip the empty .env, leaving the instance without SECRET_KEY."""
    settings.INSTANCE_DIR = tmp_path

    def broken_render(template, context):
        raise TemplateDoesNotExist(template)

    monkeypatch.setattr("dlcdb.core.management.commands.dlcdb_init.render_to_string", broken_render)

    with pytest.raises(TemplateDoesNotExist):
        call_command("dlcdb_init", stdout=io.StringIO())

    assert list(tmp_path.iterdir()) == []
