# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

# ldap/ad auth
# see: http://django-auth-ldap.readthedocs.io/en/latest/index.html

import logging
import ldap

from django_auth_ldap.config import (
    LDAPSearch,
    ActiveDirectoryGroupType,
    LDAPGroupQuery,
)

from .base import (
    AUTHENTICATION_BACKENDS,
    env,
)

# Logging stanza
# Comment out when not needed:
logger = logging.getLogger("django_auth_ldap")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


AUTH_LDAP_SERVER_URI = env.str("AUTH_LDAP_SERVER_URI")
AUTH_LDAP_BIND_DN = env.str("AUTH_LDAP_BIND_DN")
AUTH_LDAP_BIND_PASSWORD = env.str("AUTH_LDAP_BIND_PASSWORD")
AUTH_LDAP_MIRROR_GROUPS = env.list("AUTH_LDAP_MIRROR_GROUPS")

# First check ModelBackend than LDAPBackend
AUTHENTICATION_BACKENDS = AUTHENTICATION_BACKENDS + ["dlcdb.accounts.auth_backends.EmailLDAPBackend"]


AUTH_LDAP_GROUP_TYPE = ActiveDirectoryGroupType()
AUTH_LDAP_FIND_GROUP_PERMS = True
AUTH_LDAP_ALWAYS_UPDATE_USER = True
AUTH_LDAP_CACHE_TIMEOUT = 0  # 60 * 60

AUTH_LDAP_USER_SEARCH = LDAPSearch(
    f"{env.str('AUTH_LDAP_USERS_DN')}",
    ldap.SCOPE_SUBTREE,
    "(mail=%(user)s)",  # Search by email instead of sAMAccountName
)

AUTH_LDAP_GROUP_SEARCH = LDAPSearch(f"{env.str('AUTH_LDAP_USERS_DN')}", ldap.SCOPE_SUBTREE, "(objectClass=group)")

AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail",
    "username": "mail",  # Use email as username
}

# https://django-auth-ldap.readthedocs.io/en/latest/groups.html#limiting-access
AUTH_LDAP_REQUIRE_GROUP = (
    LDAPGroupQuery(env.str("AUTH_LDAP_GROUP_SUPERUSERS"))
    | LDAPGroupQuery(env.str("AUTH_LDAP_GROUP_STAFF"))
    | LDAPGroupQuery(env.str("AUTH_LDAP_REQUIRE_GROUP"))
)

AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    "is_active": AUTH_LDAP_REQUIRE_GROUP,
    "is_staff": LDAPGroupQuery(env.str("AUTH_LDAP_GROUP_SUPERUSERS"))
    | LDAPGroupQuery(env.str("AUTH_LDAP_GROUP_STAFF")),
    "is_superuser": LDAPGroupQuery(env.str("AUTH_LDAP_GROUP_SUPERUSERS")),
}

# Tweak some settings in DEV mode
if env.str("SETTINGS_MODE") == "dev":
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    # ldap.set_option(ldap.OPT_DEBUG_LEVEL, 255)
    # logger.setLevel(logging.DEBUG)
