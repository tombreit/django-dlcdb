# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Expose the *currently installed* Bootstrap Icons set to Python.

The set is derived from the shipped, compiled theme stylesheet
``dlcdb/theme/static/theme/dist/css/theme.css`` — which the frontend build
produces from the ``bootstrap-icons`` package — rather than from a hardcoded
list. Each icon contributes a rule ``.bi-<name>::before{content:"<glyph>"}``
(the literal glyph character). Reading them back therefore tracks the installed
icon set automatically: upgrading the package and rebuilding the theme adds,
renames or removes entries here with no code change.

(The package's ``bootstrap-icons.json`` is intentionally not used: it lives in
``node_modules`` and is not shipped to production, whereas ``theme.css`` is.)
"""

import functools
import re
from pathlib import Path

from django.conf import settings

_CSS_PATH = Path(settings.BASE_DIR) / "dlcdb" / "theme" / "static" / "theme" / "dist" / "css" / "theme.css"

# Matches `.bi-<name>::before{content:"<token>"}` where <token> is either the
# literal glyph char (current sass output) or an escaped codepoint (`\f1a2`).
_ICON_RE = re.compile(r'\.bi-([a-z0-9-]+)::before\{content:"(\\[0-9a-fA-F]+|.)"\}')


def _decode_token(token):
    if token.startswith("\\"):
        try:
            return chr(int(token[1:], 16))
        except ValueError:
            return ""
    return token


@functools.lru_cache(maxsize=4)
def _parse(path_str, _mtime):
    """Parse the stylesheet. Cached per (path, mtime) so a rebuilt theme is
    picked up automatically without a process restart."""
    try:
        css = Path(path_str).read_text(encoding="utf-8")
    except OSError:
        return ()

    seen = {}
    for name, token in _ICON_RE.findall(css):
        if name not in seen:
            char = _decode_token(token)
            if char:
                seen[name] = char
    return tuple(seen.items())


def get_bootstrap_icons():
    """Return ``[{"name": "<name>", "char": "<glyph>"}, …]`` for the installed
    icon set, in stylesheet order. Empty list if the stylesheet is unavailable
    (e.g. an unbuilt checkout) — callers should degrade gracefully."""
    try:
        mtime = _CSS_PATH.stat().st_mtime
    except OSError:
        return []
    return [{"name": name, "char": char} for name, char in _parse(str(_CSS_PATH), mtime)]
