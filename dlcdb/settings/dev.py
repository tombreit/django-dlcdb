from .base import *


INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

INTERNAL_IPS = ['127.0.0.1']

AUTH_PASSWORD_VALIDATORS = []

# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#enabling-middleware
#
# The order of MIDDLEWARE is important. You should include the Debug Toolbar
# middleware as early as possible in the list. However, it must come after any
# other middleware that encodes the response’s content, such as GZipMiddleware.
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

IPYTHON_ARGUMENTS = [
    '--debug',
    '--NotebookApp.iopub_data_rate_limit=10000000000.0',
]
