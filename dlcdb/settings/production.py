import os

from .base import *

if env('AUTH_LDAP'):
    from .ldap import *


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False


# Email configs
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT")
