# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The group profiles name only DLCDB's own permissions, each one that exists."""

import pytest

from dlcdb.accounts.group_profiles import GROUP_PROFILES
from dlcdb.accounts.permissions import own_permission_names


@pytest.mark.django_db
@pytest.mark.parametrize("profile", GROUP_PROFILES, ids=lambda profile: str(profile.label))
def test_a_profile_names_only_dlcdbs_own_permissions(profile):
    assert not set(profile.names) - own_permission_names()
    assert profile.permissions().count() == len(set(profile.names))
