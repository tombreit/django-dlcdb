# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The settings with ``AUTH_LDAP`` on. Settings run at import, so each case imports
``dlcdb.settings.base`` in a fresh Python process with the LDAP variables set; ``base``
reads the ``.env`` without overriding them.
"""

import json
import os
import subprocess
import sys

import pytest
from django.conf import settings

pytest.importorskip("django_auth_ldap", reason="django-auth-ldap comes with the `ldap` extra")

LDAP_ENV = {
    "DJANGO_DEBUG": "false",
    "AUTH_LDAP": "true",
    "AUTH_LDAP_SERVER_URI": "ldaps://dc.example.org",
    "AUTH_LDAP_BIND_DN": "cn=bind,dc=example,dc=org",
    "AUTH_LDAP_BIND_PASSWORD": "secret",
    "AUTH_LDAP_USERS_DN": "cn=Users,dc=example,dc=org",
    "AUTH_LDAP_MIRROR_GROUPS": "group1,group2",
    "AUTH_LDAP_REQUIRE_GROUP": "cn=dlcdb,dc=example,dc=org",
    "AUTH_LDAP_GROUP_SUPERUSERS": "cn=dlcdb-admin,dc=example,dc=org",
    "AUTH_LDAP_GROUP_STAFF": "cn=dlcdb-staff,dc=example,dc=org",
}

# Prints the settings under test as JSON.
SCRIPT = """
import json
from dlcdb.settings import base
search = getattr(base, "AUTH_LDAP_USER_SEARCH", None)
print(json.dumps({
    "backends": base.AUTHENTICATION_BACKENDS,
    "server_uri": getattr(base, "AUTH_LDAP_SERVER_URI", None),
    "group_type": type(getattr(base, "AUTH_LDAP_GROUP_TYPE", None)).__name__,
    "user_search": [search.base_dn, search.filterstr] if search else None,
    "username_attr": getattr(base, "AUTH_LDAP_USER_ATTR_MAP", {}).get("username"),
    "flags": sorted(getattr(base, "AUTH_LDAP_USER_FLAGS_BY_GROUP", {})),
}))
"""


def _load_settings(**env):
    return subprocess.run(
        [sys.executable, "-c", SCRIPT],
        cwd=settings.BASE_DIR,
        env={**os.environ, **LDAP_ENV, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def _settings(**env):
    result = _load_settings(**env)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_ldap_adds_its_backend_after_the_local_login():
    loaded = _settings()

    assert loaded["backends"] == [
        "dlcdb.accounts.auth_backends.EmailModelBackend",
        "dlcdb.accounts.ldap_backends.EmailLDAPBackend",
    ]
    assert loaded["server_uri"] == "ldaps://dc.example.org"
    assert loaded["user_search"] == ["cn=Users,dc=example,dc=org", "(|(mail=%(user)s)(sAMAccountName=%(user)s))"]
    assert loaded["username_attr"] == "sAMAccountName"
    assert loaded["flags"] == ["is_active", "is_staff", "is_superuser"]


def test_the_ldap_variant_picks_the_group_type_and_the_account_name():
    assert _settings()["group_type"] == "ActiveDirectoryGroupType"

    openldap = _settings(LDAP_VARIANT="openldap")
    assert openldap["group_type"] == "PosixGroupType"
    assert openldap["user_search"][1] == "(|(mail=%(user)s)(uid=%(user)s))"
    assert openldap["username_attr"] == "uid"


def test_an_unknown_ldap_variant_stops_the_start():
    result = _load_settings(LDAP_VARIANT="novell")

    assert result.returncode != 0
    assert "Unsupported LDAP_VARIANT='novell'" in result.stderr


def test_without_ldap_only_the_local_login_is_configured():
    loaded = _settings(AUTH_LDAP="false")

    assert loaded["backends"] == ["dlcdb.accounts.auth_backends.EmailModelBackend"]
    assert loaded["server_uri"] is None
