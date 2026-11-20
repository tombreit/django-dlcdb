# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import pytest


@pytest.fixture
def login(client, make_user):
    """Log in a user without the Staff flag: the pages need no admin access."""

    def _login(*perms):
        user = make_user(*perms, email="editor@example.com")
        client.force_login(user)
        return user

    return _login
