from .base import env

# Choosing the settings which fit to our current environment.

if env('SETTINGS_MODE') == 'dev':
    from .dev import *
else:
    from .production import *
