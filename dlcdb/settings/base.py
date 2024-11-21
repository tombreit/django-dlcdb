# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from pathlib import Path
from email.utils import getaddresses
import environ
from huey import SqliteHuey


BASE_DIR = Path(__file__).resolve().parent.parent.parent
RUN_DIR = BASE_DIR / "run"
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
MEDIA_DIR = DATA_DIR / "media"
STATICFILES_DIR = RUN_DIR / "staticfiles"

# Make sure directory structure exists
Path(DB_DIR).mkdir(parents=True, exist_ok=True)
Path(MEDIA_DIR).mkdir(parents=True, exist_ok=True)
Path(STATICFILES_DIR).mkdir(parents=True, exist_ok=True)

# Take environment variables from .env file
env = environ.Env(
    SETTINGS_MODE=(str, "dev"),
    DJANGO_DEBUG=(bool, True),
    AUTH_LDAP=(bool, False),
    SECRET_KEY=(str, "!set-your-secretkey-via-dot-env-file!"),
    ADMINS=(str, ""),
)
environ.Env.read_env(BASE_DIR / ".env")

DEV_SETTINGS_MODE = True if env("SETTINGS_MODE") == "dev" else False
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
    "django.contrib.staticfiles",
    "django.contrib.sites",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "crispy_forms",
    "crispy_bootstrap4",
    "django_select2",
    "django_htmx",
    "huey.contrib.djhuey",
    "simple_history",
    "whitenoise.runserver_nostatic",
]
LOCAL_APPS = [
    "dlcdb.accounts",
    "dlcdb.tenants",
    "dlcdb.core",
    "dlcdb.organization",
    "dlcdb.inventory",
    "dlcdb.licenses",
    "dlcdb.reporting",
    "dlcdb.lending",
    "dlcdb.smallstuff",
    "dlcdb.api",
    "dlcdb.theme",
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

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

SITE_ID = 1

AUTH_USER_MODEL = "accounts.CustomUser"

# Email these people full exception information
# https://docs.djangoproject.com/en/1.9/ref/settings/#admins
# https://django-environ.readthedocs.io/en/latest/tips.html#nested-lists
ADMINS = getaddresses([env("ADMINS")])
MANAGERS = ADMINS
EMAIL_SUBJECT_PREFIX = env.str("EMAIL_SUBJECT_PREFIX", default="[DLCDB] ")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="mail@example.org")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_BACKEND = env.str("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env.str("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=0)

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
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dlcdb.core.context_processors.hints",
                "dlcdb.core.context_processors.nav",
                "dlcdb.organization.context_processors.branding",
            ],
        },
    },
]

WSGI_APPLICATION = "dlcdb.wsgi.application"

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': str(DB_DIR / 'db.sqlite3'),
    # },
    "default": env.db_url(default=f"sqlite:////{DB_DIR / 'db.sqlite3'}"),
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    # 'default': {
    #     'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
    #     'LOCATION': '127.0.0.1:11211',  # Docker notation: 'memcached:11211', see docker-compose
    # },
    # 'select2': {
    #     'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
    #     'LOCATION': '127.0.0.1:11211',
    # },
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "select2": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "dlcdb_select2",
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

if DEV_SETTINGS_MODE:
    AUTH_PASSWORD_VALIDATORS = []


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

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"

DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000  # default is: 1000

SELECT2_CACHE_BACKEND = "select2"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

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
    # 'PAGE_SIZE': 10,
}

# https://django-simple-history.readthedocs.io/en/latest/admin.html#disabling-the-option-to-revert-an-object
SIMPLE_HISTORY_REVERT_DISABLED = True
SIMPLE_HISTORY_FILEFIELD_TO_CHARFIELD = True


HUEY = SqliteHuey(
    name="dlcdb_huey",
    filename=str(DB_DIR / "huey_task_queue.sqlite3"),
)

# WhiteNoise
WHITENOISE_INDEX_FILE = True

# Add extra output directories that WhiteNoise can serve as static files
# *outside* of `staticfiles`.
MORE_WHITENOISE = [
    {"directory": BASE_DIR / "run" / "docs" / "html", "prefix": "docs/"},
]

# Reporting
REPORTING_NOTIFY_OVERDUE_LENDERS = env.bool("REPORTING_NOTIFY_OVERDUE_LENDERS", default=True)
REPORTING_NOTIFY_OVERDUE_LENDERS_TO_IT = env.bool("REPORTING_NOTIFY_OVERDUE_LENDERS", default=True)

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
MAX_FUTURE_LENT_DESIRED_END_DATE = "2099-12-31"

UDB_INTEGRATION = env.bool("UDB_INTEGRATION", default=False)
UDB_JSON_URL = env("UDB_JSON_URL", default=None)
UDB_API_TOKEN = env("UDB_API_TOKEN", default=None)

PERSON_IMAGE_UPLOAD_DIR = "person_images"

DEVICE_HIDE_FIELDS = env.list("DEVICE_HIDE_FIELDS", default=[])

# TODO: Move icon and color to class var for base model?
THEME = {
    "core.record": {
        "ICON": "fa-solid fa-layer-group",
        "COLOR": "",
    },
    "core.device": {
        "ICON": "fa-solid fa-barcode",
        "COLOR": "",
    },
    "core.devicetype": {
        "ICON": "fa-solid fa-palette",
        "COLOR": "",
    },
    "core.room": {
        "ICON": "fa-solid fa-door-open",
        "COLOR": "",
    },
    "core.lentrecord": {
        "ICON": "fa-solid fa-arrow-right-arrow-left",
        "COLOR": "",
    },
    "core.lostrecord": {
        "ICON": "fa-solid fa-layer-group",
        "COLOR": "",
    },
    "core.licencerecord": {
        "ICON": "fa-solid fa-scale-balanced",
        "COLOR": "",
    },
    "core.inventory": {
        "ICON": "fa-solid fa-glasses",
        "COLOR": "",
    },
    "core.manufacturer": {
        "ICON": "fa-solid fa-industry",
        "COLOR": "",
    },
    "core.supplier": {
        "ICON": "fa-solid fa-truck",
        "COLOR": "",
    },
    "smallstuff.assignedthing": {
        "ICON": "fa-solid fa-stapler",
        "COLOR": "",
    },
}

# https://django-extensions.readthedocs.io/en/latest/shell_plus.html#configuration
# IPYTHON_ARGUMENTS = [
#     '--debug',
#     '--NotebookApp.iopub_data_rate_limit=10000000000.0',
# ]

if env("AUTH_LDAP"):
    from .ldap import *  # NOQA
    # print("[i] AUTH_LDAP activated via .env")
else:
    # print("[i] AUTH_LDAP disabled in .env")
    pass
