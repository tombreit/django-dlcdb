# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Every static file a template names exists. In production the manifest storage
fails the page on a path it doesn't know; the tests render with the plain
storage (``settings/test.py``), which builds a URL for any path. Paths in a
``dist/`` directory exist only after ``npm run build``.
"""

import re
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders

import dlcdb

STATIC_TAG = re.compile(r"""{%\s*static\s+["']([^"']+)["']""")
DIST_DIRECTORY = re.compile(r"(.*?\bdist)/")

TEMPLATES = Path(dlcdb.__file__).parent.glob("**/templates/**/*.html")
STATIC_PATHS = sorted({path for template in TEMPLATES for path in STATIC_TAG.findall(template.read_text())})


@pytest.mark.parametrize("path", STATIC_PATHS)
def test_the_static_file_a_template_names_exists(path):
    dist = DIST_DIRECTORY.match(path)
    if dist and not finders.find(dist[1]):
        pytest.skip(f"{dist[1]} is built by npm run build")
    assert finders.find(path)
