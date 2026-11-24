# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailModelBackend(ModelBackend):
    """
    Log in with the email address (``USERNAME_FIELD``) or the username.

    The class keeps its name, although it takes usernames too: sessions store the
    backend's path, so a new name would log everyone out.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        users = UserModel._default_manager
        # The email wins: many usernames are (former) email addresses.
        if username and not users.filter(email=username).exists():
            username = users.filter(username=username).values_list("email", flat=True).first() or username
        return super().authenticate(request, username, password, **kwargs)
