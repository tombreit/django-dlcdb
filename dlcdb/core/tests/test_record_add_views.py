# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The admin adds no ordered, room-assignment, not-locatable or removed records.

Its add-forms checked only "Can add <record>", not the transition permission, so a
staff user could e.g. recover a decommissioned device without being allowed to.
State changes run in the frontend, gated by their transition permission.
"""

import pytest
from django.urls import reverse

from dlcdb.core.models import RemovedRecord


@pytest.mark.django_db
@pytest.mark.parametrize("model_name", ["orderedrecord", "inroomrecord", "lostrecord", "removedrecord"])
def test_the_add_permission_opens_no_add_form(client, plain_static, make_user, join_tenant, plain_device, model_name):
    RemovedRecord.objects.create(device=plain_device)
    user = make_user(f"core.add_{model_name}", f"core.view_{model_name}", is_staff=True)
    client.force_login(join_tenant(user))
    add_url = reverse(f"admin:core_{model_name}_add")

    assert client.get(add_url, {"device": plain_device.pk}).status_code == 403
    assert add_url not in client.get(reverse(f"admin:core_{model_name}_changelist")).text
