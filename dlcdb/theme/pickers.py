# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Registry of device-picker *data sources*.

The device picker (widget, card, results partial, JS, search helper) is generic
and only ever handles ``core.Device`` querysets. The one thing that differs
between callers — which devices are offered and which permission guards them —
is described here as a ``PickerSource`` and registered by the owning app at
``AppConfig.ready()``. The shared search endpoint (``theme.views.device_search``)
looks the source up by its ``name`` (a POST ``source`` token), so ``theme`` never
imports lending/assets models and there is no circular dependency.

A source carries *no* rendering or card configuration: base-queryset
construction (including tenant scoping) lives entirely in the owning app's
``get_queryset`` callable.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from django.db.models import QuerySet
from django.http import HttpRequest


@dataclass(frozen=True)
class PickerSource:
    name: str  # POST `source` token, e.g. "lend" / "move"
    permission: str  # required perm, e.g. "core.change_lentrecord"
    get_queryset: Callable[[HttpRequest], QuerySet]  # tenant-scoped Device queryset
    search_param: str  # name of the search input, e.g. "q" / "q_device"
    multiple: bool  # single- vs multi-select picker
    # Multi-select only: name of the per-card hidden inputs carrying the already
    # picked pks, sent along with each live search (hx-include) so they drop out
    # of the results.
    exclude_param: Optional[str] = None


_REGISTRY: dict[str, PickerSource] = {}


def register_picker_source(source: PickerSource) -> None:
    """Register (or replace) a picker data source. Idempotent per ``name``."""
    _REGISTRY[source.name] = source


def get_picker_source(name) -> Optional[PickerSource]:
    """Return the registered source for ``name`` (or ``None`` if unknown)."""
    return _REGISTRY.get(name) if name else None
