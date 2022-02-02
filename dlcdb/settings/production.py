import os

from .base import *
from .ldap import *


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False


# ALLOWED_HOSTS, bei DEBUG = True ignoriert
# https://docs.djangoproject.com/en/1.9/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    'dlcdb-it.csl.mpg.de',
    'dlcdb-it.mpicc.de',
    'dlcdb-verwaltung.csl.mpg.de',
    'dlcdb-verwaltung.mpicc.de',
]

# Email these people full exception information
# https://docs.djangoproject.com/en/1.9/ref/settings/#admins
ADMINS = [
    ('Thomas Breitner', 't.breitner@csl.mpg.de'),
]

# Email configs
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.mpicc.de'
EMAIL_PORT = 25
