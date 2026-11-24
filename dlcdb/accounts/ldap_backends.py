# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The LDAP authentication backend, only used with AUTH_LDAP (dlcdb/settings/base.py).

It lives apart from auth_backends.py, because django_auth_ldap is installed only
with the `ldap` extra.
"""

from django_auth_ldap.backend import LDAPBackend


class EmailLDAPBackend(LDAPBackend):
    """
    Users log in with their email address or their account name
    (AUTH_LDAP_USER_SEARCH); either way, their Django user is the one with the
    entry's email address. The stock lookup goes by what was typed in, so an
    account name would get a second user.
    """

    def get_or_build_user(self, username, ldap_user):
        # ldap_user.attrs is a case-insensitive dict; the lookup is email__iexact (USERNAME_FIELD).
        mail = ldap_user.attrs.get("mail")
        if not mail:
            raise ldap_user.AuthenticationFailed("the LDAP entry has no mail attribute")
        return super().get_or_build_user(mail[0], ldap_user)
