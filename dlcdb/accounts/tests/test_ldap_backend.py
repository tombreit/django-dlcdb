# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Which Django user an LDAP login gets, whether the email or the account name was typed in."""

from types import SimpleNamespace

import pytest

pytest.importorskip("django_auth_ldap", reason="django-auth-ldap comes with the `ldap` extra")

from django_auth_ldap.backend import _LDAPUser

from dlcdb.accounts.ldap_backends import EmailLDAPBackend
from dlcdb.accounts.models import CustomUser


def _entry(**attrs):
    return SimpleNamespace(attrs=attrs, AuthenticationFailed=_LDAPUser.AuthenticationFailed)


@pytest.mark.django_db
def test_an_account_name_login_finds_the_user_by_the_entrys_email():
    # Created on New user before the first LDAP login, the email in lower case.
    ada = CustomUser.objects.create_user(email="ada@example.com", username="ada")

    user, built = EmailLDAPBackend().get_or_build_user("alovelace", _entry(mail=["Ada@Example.com"]))

    assert (user, built) == (ada, False)


@pytest.mark.django_db
def test_a_new_ldap_user_is_built_with_the_entrys_email():
    user, built = EmailLDAPBackend().get_or_build_user("alovelace", _entry(mail=["ada@example.com"]))

    assert built
    assert user.email == "ada@example.com"


def test_an_entry_without_mail_fails_the_login():
    with pytest.raises(_LDAPUser.AuthenticationFailed):
        EmailLDAPBackend().get_or_build_user("alovelace", _entry())
