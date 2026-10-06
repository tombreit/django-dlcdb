# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import os
from email.utils import getaddresses
from pathlib import Path

import environ
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from huey import SqliteHuey

import dlcdb

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# A source checkout has pyproject.toml next to the dlcdb package; a pip installation has not.
SOURCE_CHECKOUT = (BASE_DIR / "pyproject.toml").exists()

# The instance directory holds .env and data/ (a source checkout also run/). A source
# checkout uses the repository root; a pip installation names it via the DLCDB_HOME
# environment variable.
if os.environ.get("DLCDB_HOME"):
    INSTANCE_DIR = Path(os.environ["DLCDB_HOME"]).resolve()
elif SOURCE_CHECKOUT:
    INSTANCE_DIR = BASE_DIR
else:
    raise ImproperlyConfigured(
        "DLCDB is not running from a source checkout: set the DLCDB_HOME environment variable "
        "to the instance directory, which holds .env and data/."
    )

RUN_DIR = INSTANCE_DIR / "run"
DATA_DIR = INSTANCE_DIR / "data"
DB_DIR = DATA_DIR / "db"
MEDIA_DIR = DATA_DIR / "media"
# Collected static files: `collectstatic` writes them to run/staticfiles in a source
# checkout; a wheel carries them inside the package (collected by the release build).
STATICFILES_DIR = RUN_DIR / "staticfiles" if SOURCE_CHECKOUT else BASE_DIR / "dlcdb" / "staticfiles"

# Make sure directory structure exists
Path(DB_DIR).mkdir(parents=True, exist_ok=True)
Path(MEDIA_DIR).mkdir(parents=True, exist_ok=True)
Path(STATICFILES_DIR).mkdir(parents=True, exist_ok=True)

# Take environment variables from .env file
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    AUTH_LDAP=(bool, False),
    SECRET_KEY=(str, "!set-your-secretkey-via-dot-env-file!"),
    ADMINS=(str, ""),
)
environ.Env.read_env(INSTANCE_DIR / ".env")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG")
SECRET_KEY = env("SECRET_KEY")

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Must be *before* django.contrib.staticfiles
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "drf_spectacular",
    "crispy_forms",
    "crispy_bootstrap5",
    "django_htmx",
    "huey.contrib.djhuey",
    "simple_history",
]
LOCAL_APPS = [
    "dlcdb.accounts",
    "dlcdb.tenants",
    "dlcdb.core",
    "dlcdb.dataexchange",
    "dlcdb.organization",
    "dlcdb.inventory",
    "dlcdb.licenses",
    "dlcdb.reporting",
    "dlcdb.notifications",
    "dlcdb.lending",
    "dlcdb.smallstuff",
    "dlcdb.assets",
    "dlcdb.rooms",
    "dlcdb.persons",
    "dlcdb.api",
    "dlcdb.theme",
    "dlcdb.dashboard",
    "dlcdb.journal",
]
DEV_APPS = [
    "debug_toolbar",
    "django_extensions",
]


# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

if DEBUG:
    INSTALLED_APPS = INSTALLED_APPS + DEV_APPS

# https://docs.djangoproject.com/en/1.9/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-trusted-origins
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# https://docs.djangoproject.com/en/3.0/ref/clickjacking/#setting-x-frame-options-for-all-responses
X_FRAME_OPTIONS = "SAMEORIGIN"

# https://docs.djangoproject.com/en/dev/ref/settings/#internal-ips
INTERNAL_IPS = ["127.0.0.1"] if DEBUG else []

AUTH_USER_MODEL = "accounts.CustomUser"
LOGIN_FIELD = "email"
AUTHENTICATION_BACKENDS = [
    # "django.contrib.auth.backends.ModelBackend",
    "dlcdb.accounts.auth_backends.EmailModelBackend",
]


SITE_ID = 1

# Email these people full exception information
# https://docs.djangoproject.com/en/1.9/ref/settings/#admins
# https://django-environ.readthedocs.io/en/latest/tips.html#nested-lists
ADMINS = getaddresses([env("ADMINS")])
MANAGERS = ADMINS
EMAIL_SUBJECT_PREFIX = env.str("EMAIL_SUBJECT_PREFIX", default="[DLCDB] ")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="mail@example.org")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
MAILERS = {
    "default": {
        "BACKEND": env.str("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"),
    },
}
# Only SMTP-like backends accept host/port; the console backend rejects unknown OPTIONS.
if env.str("EMAIL_HOST", default=""):
    MAILERS["default"]["OPTIONS"] = {"host": env.str("EMAIL_HOST"), "port": env.int("EMAIL_PORT", default=25)}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Using our customized WhiteNoiseMiddleware to serve additional static files (here: /docs/)
    # "whitenoise.middleware.WhiteNoiseMiddleware",
    "dlcdb.core.middleware.MoreWhiteNoiseMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "dlcdb.tenants.middleware.CurrentTenantMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#enabling-middleware
#
# The order of MIDDLEWARE is important. You should include the Debug Toolbar
# middleware as early as possible in the list. However, it must come after any
# other middleware that encodes the response’s content, such as GZipMiddleware.
if DEBUG:
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

ROOT_URLCONF = "dlcdb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "dlcdb/templates")],
        "OPTIONS": {
            "loaders": [
                "dlcdb.lending.loader.DatabaseLoader",
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dlcdb.core.context_processors.hints",
                "dlcdb.core.context_processors.nav",
                "dlcdb.core.context_processors.django_settings",
                "dlcdb.theme.context_processors.project_meta",
                "dlcdb.organization.context_processors.branding",
                "dlcdb.inventory.context_processors.inventory",
            ],
        },
    },
]

WSGI_APPLICATION = "dlcdb.wsgi.application"

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    "default": env.db_url(default=f"sqlite:////{DB_DIR / 'db.sqlite3'}"),
}

# SQLite tuned for several writers on one file: the web server (Apache mod_wsgi,
# by default one process with 15 threads; or the gunicorn workers of the
# container) and the huey consumer, and during a deploy also `migrate` while the
# old processes still run. Requires Django >= 5.1 for init_command and
# transaction_mode.
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    DATABASES["default"]["OPTIONS"] = {
        # WAL lets readers run while a writer holds the lock, instead of reads
        # and writes blocking each other. The mode is stored in the file
        # header, so this only actually flips it on the first connect. Backups
        # copy the nightly snapshot instead of the live file (core/tasks.py,
        # docs/betrieb/setup.md).
        #
        # synchronous=NORMAL is the safe pairing for WAL: a process crash loses
        # nothing; only an OS crash or power loss can lose the most recently
        # committed transactions.
        #
        # cache_size is negative, which means KiB rather than pages: up to 20 MB
        # per connection (one per thread), filled only as pages are read.
        # mmap_size maps up to 128 MB of the file, shared through the OS page
        # cache.
        "init_command": (
            "PRAGMA journal_mode=WAL;"
            "PRAGMA synchronous=NORMAL;"
            "PRAGMA temp_store=MEMORY;"
            "PRAGMA mmap_size=134217728;"  # 128 MB
            "PRAGMA journal_size_limit=27103364;"  # ~26 MB, caps WAL growth
            "PRAGMA cache_size=-20000;"  # 20 MB
        ),
        # Take the write lock at BEGIN rather than upgrading to it mid
        # transaction. A lock upgrade cannot wait for `timeout` -- it fails
        # immediately with "database is locked", as a data migration did while
        # huey was writing -- so IMMEDIATE turns those errors into a wait.
        # Django's docs warn against combining this with ATOMIC_REQUESTS; this
        # project does not set it.
        "transaction_mode": "IMMEDIATE",
        # Busy timeout in seconds (Python's default is 5). Deploys run `migrate`
        # while the old web workers (and huey, unless stopped) still run, so
        # leave more room than the default.
        "timeout": 20,
    }

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    # 'default': {
    #     'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
    #     'LOCATION': '127.0.0.1:11211',  # Docker notation: 'memcached:11211', see docker-compose
    # },
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = "de-de"
USE_I18N = True

LANGUAGES = (
    ("de", "Deutsch"),
    ("en-us", "English"),
)

LOCALE_PATHS = [
    BASE_DIR / "dlcdb" / "locale",
]

# https://docs.djangoproject.com/en/dev/ref/settings/#std-setting-TIME_ZONE
USE_TZ = True
TIME_ZONE = "Europe/Berlin"  # 'UTC'

# https://docs.djangoproject.com/en/4.0/topics/i18n/formatting/#creating-custom-format-files
FORMAT_MODULE_PATH = [
    "dlcdb.core.formats",
]

# https://docs.djangoproject.com/en/4.1/ref/contrib/sites/#enabling-the-sites-framework
SITE_ID = 1

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATICFILES_DIRS = [
    BASE_DIR / "dlcdb" / "static",
]

STATIC_ROOT = STATICFILES_DIR
STATIC_URL = "/static/"

MEDIA_ROOT = MEDIA_DIR
MEDIA_URL = "/media/"

# http://whitenoise.evans.io/en/latest/django.html#add-compression-and-caching-support
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",  # "whitenoise.storage.CompressedStaticFilesStorage"
    },
}

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "logout"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    # Copied from Django's DEFAULT_LOGGING, for the mail_admins handler below.
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "formatters": {
        "simple": {
            "format": "{levelname} {name} {message}",
            "style": "{",
        },
        # Copied from Django's DEFAULT_LOGGING, for the runserver access log.
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        # Copied from Django's DEFAULT_LOGGING. Its own "level" is what gates
        # email — only ERROR and above are sent, regardless of the level on the
        # loggers that feed it.
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        # Copied from Django's DEFAULT_LOGGING.
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        # Copy anomalies into the journal (dlcdb.journal.handlers). Never attach
        # these to django.db.backends: every query would recurse into an insert.
        "journal": {
            "level": "WARNING",
            "class": "dlcdb.journal.handlers.JournalHandler",
        },
        "journal_errors": {
            "level": "ERROR",
            "class": "dlcdb.journal.handlers.JournalHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        # Django's DEFAULT_LOGGING attaches its own unformatted console handler
        # here. Claim the logger, or every request is logged twice: once bare by
        # that handler, once via root.
        "django": {
            "handlers": ["console", "mail_admins"],
            "level": "INFO",
            "propagate": False,
        },
        # Claiming "django" above resets its child loggers, so restore Django's
        # own entry verbatim to keep the runserver access log timestamped.
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
        # Unhandled exceptions in views (500s) into the journal. No level of its
        # own and propagating, so "django" still prints 404/403 warnings and
        # mails 500s as before.
        "django.request": {
            "handlers": ["journal_errors"],
            "propagate": True,
        },
        "dlcdb": {
            "handlers": ["console", "journal"],
            "level": "DEBUG" if DEBUG else "WARNING",
            "propagate": False,
        },
        # Suppress noisy Huey INFO messages (only WARNING+ will be emitted)
        "huey": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


MESSAGE_TAGS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}

DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000  # default is: 1000

CRISPY_FAIL_SILENTLY = not DEBUG
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # 'PAGE_SIZE': 10,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "DLCDB API",
    "DESCRIPTION": "Device Life Cycle Database API",
    "VERSION": dlcdb.__version__,
    "SERVE_INCLUDE_SCHEMA": False,
}

# https://django-simple-history.readthedocs.io/en/latest/admin.html#disabling-the-option-to-revert-an-object
SIMPLE_HISTORY_REVERT_DISABLED = True
SIMPLE_HISTORY_FILEFIELD_TO_CHARFIELD = True


# results=False: nothing reads task results, and the SQLite backend keeps them
# forever (no expiry). Storing them grew the queue file to 7 GB in production.
# Failures still reach the log and the journal (dlcdb/journal/signals.py).
HUEY = SqliteHuey(
    name="dlcdb_huey",
    filename=str(DB_DIR / "huey_task_queue.sqlite3"),
    results=False,
)

if DEBUG:
    DEBUG_TOOLBAR_CONFIG = {"ROOT_TAG_EXTRA_ATTRS": "hx-preserve"}
    MIGRATION_MODULES = {"debug_toolbar": None}
    SHELL_PLUS = "ipython"

# WhiteNoise
WHITENOISE_INDEX_FILE = True
# A wheel's collected static files match the dependency versions of its release build. If a
# newer dependency refers to a static file missing there, fall back to the unhashed name
# instead of failing the whole page.
WHITENOISE_MANIFEST_STRICT = SOURCE_CHECKOUT

# Built docs, served at /docs/: `make docs` writes them to run/docs/html in a source
# checkout; a wheel carries them inside the package (copied there by the release build).
DOCS_DIR = BASE_DIR / "run" / "docs" / "html" if SOURCE_CHECKOUT else BASE_DIR / "dlcdb" / "docs_html"

# Add extra output directories that WhiteNoise can serve as static files
# *outside* of `staticfiles`.
MORE_WHITENOISE = [
    {"directory": DOCS_DIR, "prefix": "docs/"},
]

DLCDB_BASE_URL = env("DLCDB_BASE_URL", default="http://127.0.0.1:8000")

# Overdue-lender notification flags now live on the LendingConfiguration
# singleton (admin-editable); see dlcdb/lending/models.py.

# Inventory/Scanner

# QRCODE_PREFIX (string) is used to prefix all generated uuids in qr codes
# in order to let the scanner deceide if a scanned qr code should be handled by
# this application.
# DO NOT CHANGE THIS PREFIX MID-PROJECT AS IT WILL BREAK THE SCANNER RECOGNIZING
# ALREADY PRINTED QR CODES.
QRCODE_DIR = "qrcode"
QRCODE_PREFIX = "DLCDB"
QRCODE_INFIXES = {
    "room": "R",
    "device": "D",
}

SAP_LIST_COMPARISON_RESULT_FOLDER = "sap_list_comparison_results"
MAX_FUTURE_LENT_DESIRED_END_DATE = env.str("MAX_FUTURE_LENT_DESIRED_END_DATE", default="2099-12-31")

# UDB integration is configured at runtime via the admin-managed
# `dlcdb.dataexchange.models.UdbSyncConfiguration` singleton, not via env/settings.

PERSON_IMAGE_UPLOAD_DIR = "person_images"

DEVICE_HIDE_FIELDS = env.list("DEVICE_HIDE_FIELDS", default=[])

# TODO: Move icon and color to class var for base model?
THEME = {
    "core.record": {
        "ICON": "bi bi-stack",
        "COLOR": "",
    },
    "core.device": {
        "ICON": "bi bi-upc",
        "COLOR": "",
    },
    "core.devicetype": {
        "ICON": "bi bi-palette",
        "COLOR": "",
    },
    "core.room": {
        "ICON": "bi bi-door-open",
        "COLOR": "",
    },
    "core.lentrecord": {
        "ICON": "bi bi-arrow-left-right",
        "COLOR": "",
    },
    "core.lostrecord": {
        "ICON": "bi bi-stack",
        "COLOR": "",
    },
    "core.licencerecord": {
        "ICON": "bi bi-bank2",
        "COLOR": "",
    },
    "core.inventory": {
        "ICON": "bi bi-eyeglasses",
        "COLOR": "",
    },
    "core.manufacturer": {
        "ICON": "bi bi-building",
        "COLOR": "",
    },
    "core.supplier": {
        "ICON": "bi bi-truck",
        "COLOR": "",
    },
    "smallstuff.assignedthing": {
        "ICON": "bi bi-handbag",
        "COLOR": "",
    },
}

# https://django-extensions.readthedocs.io/en/latest/shell_plus.html#configuration
# IPYTHON_ARGUMENTS = [
#     '--debug',
#     '--NotebookApp.iopub_data_rate_limit=10000000000.0',
# ]

if env("AUTH_LDAP"):
    from .ldap import *
    # print("[i] AUTH_LDAP activated via .env")
else:
    # print("[i] AUTH_LDAP disabled in .env")
    pass
