# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The LDAP authentication backend, only used with AUTH_LDAP (dlcdb/settings/ldap.py).

It lives apart from auth_backends.py, because django_auth_ldap is installed only
with the `ldap` extra.
"""

from django.contrib.auth import get_user_model
from django_auth_ldap.backend import LDAPBackend


class EmailLDAPBackend(LDAPBackend):
    def get_or_create_user(self, username, ldap_user):
        UserModel = get_user_model()
        email = ldap_user.attrs.get("mail", [None])[0]
        if not email:
            raise ValueError("LDAP user does not have a 'mail' attribute; cannot authenticate without email.")

        try:
            user = UserModel.objects.get(email__iexact=email)
            return user, False
        except UserModel.DoesNotExist:
            return super().get_or_create_user(username, ldap_user)
