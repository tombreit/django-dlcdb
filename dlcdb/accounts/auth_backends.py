# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth.backends import ModelBackend


class EmailModelBackend(ModelBackend):
    """
    Authenticate normally, but ensure username matches email after successful login
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # First try standard authentication
        user = super().authenticate(request, username, password, **kwargs)

        # If authentication succeeded, ensure username matches email
        if user:
            if user.username != user.email:
                user.username = user.email
                user.save(update_fields=["username"])

        return user
