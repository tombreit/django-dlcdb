# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The icon of a model: a Bootstrap Icons class, keyed by ``"app_label.model_name"``.
Shown on the dashboard tiles and in the admin's note badge.
"""

MODEL_ICONS = {
    "core.record": "bi bi-stack",
    "core.device": "bi bi-pc-display",
    "core.devicetype": "bi bi-palette",
    "core.room": "bi bi-door-open",
    "core.lentrecord": "bi bi-arrow-left-right",
    "core.lostrecord": "bi bi-question-circle",
    "core.licencerecord": "bi bi-bank2",
    "core.inventory": "bi bi-eyeglasses",
    "core.manufacturer": "bi bi-building",
    "core.supplier": "bi bi-truck",
    "smallstuff.assignedthing": "bi bi-handbag",
}


def get_icon_for_class(class_name):
    """The icon class for ``"app_label.model_name"``, or an empty string."""
    return MODEL_ICONS.get(class_name, "")
