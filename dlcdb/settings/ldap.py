# ldap/ad auth
# see: http://django-auth-ldap.readthedocs.io/en/latest/index.html

import logging
import ldap

from django_auth_ldap.config import (
    LDAPSearch,
    LDAPSearchUnion,
    ActiveDirectoryGroupType,
    LDAPGroupQuery,
)

from .base import (
    AUTHENTICATION_BACKENDS,
    get_evncontext,
)

# Logging stanza
# Comment out when not needed:
logger = logging.getLogger('django_auth_ldap')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


# Concat available ldap groups
# def get_required_groups():
#     ldap_group_querys = []

#     for group in get_evncontext('LDAP_ACCESS_GROUPS'):
#         ldap_group_querys.append(
#             LDAPGroupQuery(
#                 'cn={0},cn=Users,dc=mpicc,dc=de'.format(group)
#             )
#         )
#     print("ldap_group_querys: ", ldap_group_querys)


AUTHENTICATION_BACKENDS += [
    'django_auth_ldap.backend.LDAPBackend',
]


AUTH_LDAP_GLOBAL_OPTIONS = {
    # ldap.OPT_PROTOCOL_VERSION: 3,
    # ldap.OPT_REFERRALS: 0,
    # ldap.OPT_X_TLS_CACERTFILE: '/etc/ssl/localcerts/radiusi.pem',
}

if get_evncontext('SETTINGS_MODE') == 'dev':
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    # ldap.set_option(ldap.OPT_DEBUG_LEVEL, 255)


AUTH_LDAP_SERVER_URI = "ldaps://rodc.mpicc.de"

AUTH_LDAP_BIND_DN = 'cn={},ou=Hidden AD Objects,dc=mpicc,dc=de'.format(
    get_evncontext('LDAP_QUERY_USERNAME')
)
AUTH_LDAP_BIND_PASSWORD = get_evncontext('LDAP_QUERY_PASSWORD')

AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(
    LDAPSearch("cn=Users,dc=mpicc,dc=de", ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)"),
)

AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    "cn=Users,dc=mpicc,dc=de",
    ldap.SCOPE_SUBTREE,
    "(objectClass=group)"
)

AUTH_LDAP_GROUP_TYPE = ActiveDirectoryGroupType()
AUTH_LDAP_MIRROR_GROUPS = True
AUTH_LDAP_FIND_GROUP_PERMS = True
AUTH_LDAP_CACHE_TIMEOUT = (60 * 60)

AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail"
}

# https://django-auth-ldap.readthedocs.io/en/latest/groups.html#limiting-access
AUTH_LDAP_REQUIRE_GROUP = (
    LDAPGroupQuery("cn=itadmin,cn=Users,dc=mpicc,dc=de") | 
    LDAPGroupQuery("cn=edv,cn=Users,dc=mpicc,dc=de") |
    LDAPGroupQuery("cn=dlcdb,cn=Users,dc=mpicc,dc=de") 
)

AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    "is_active": (
        LDAPGroupQuery("cn=edv,cn=Users,dc=mpicc,dc=de") |
        LDAPGroupQuery("cn=dlcdb,cn=Users,dc=mpicc,dc=de") 
    ),
    "is_staff": (
        LDAPGroupQuery("cn=edv,cn=Users,dc=mpicc,dc=de") |
        LDAPGroupQuery("cn=dlcdb,cn=Users,dc=mpicc,dc=de") 
    ),
    "is_superuser": (
        LDAPGroupQuery("cn=django_admins,ou=Hidden AD Objects,dc=mpicc,dc=de")
    ),
}
