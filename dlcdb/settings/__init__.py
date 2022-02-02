from .base import get_evncontext

# Choosing the settings which fit to our current environment.

if get_evncontext('SETTINGS_MODE') == 'dev':
    from .dev import *
else:
    from .production import *
