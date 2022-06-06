import json
from pathlib import Path
import environ
from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static
from huey import SqliteHuey


BASE_DIR = Path(__file__).resolve().parent.parent.parent

RUN_DIR = BASE_DIR / "run"
DB_DIR = RUN_DIR / "db"
IMPORT_DIR = RUN_DIR / "import"
MEDIA_DIR = RUN_DIR / "media"
STATICFILES_DIR = RUN_DIR / "staticfiles"

# Make sure directory structure exists
Path(DB_DIR).mkdir(parents=True, exist_ok=True)
Path(IMPORT_DIR).mkdir(parents=True, exist_ok=True)
Path(MEDIA_DIR).mkdir(parents=True, exist_ok=True)
Path(STATICFILES_DIR).mkdir(parents=True, exist_ok=True)

# Take environment variables from .env file
env = environ.Env()
environ.Env.read_env(BASE_DIR /'.env')

SECRET_KEY = env('SECRET_KEY')

# Email these people full exception information
# https://docs.djangoproject.com/en/1.9/ref/settings/#admins
ADMINS = [x.split(':') for x in env.list('ADMINS')]
MANAGERS = ADMINS
# print(f"{ADMINS=}")
# print(f"{type(ADMINS)=}")

# https://docs.djangoproject.com/en/1.9/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
# print(f"{ALLOWED_HOSTS=}")
# print(f"{type(ALLOWED_HOSTS)=}")


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'crispy_forms',
    'django_select2',
    'django_htmx',
    'huey.contrib.djhuey',
    'simple_history',
]
LOCAL_APPS = [
    'dlcdb.accounts',
    'dlcdb.tenants',
    'dlcdb.core',
    'dlcdb.inventory',
    'dlcdb.reporting',
    'dlcdb.lending',
    'dlcdb.smallstuff',
    'dlcdb.api',
]

# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = 'accounts.CustomUser'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'dlcdb.tenants.middleware.CurrentTenantMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dlcdb.lending.middleware.htmx_middleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'dlcdb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [str(BASE_DIR / 'dlcdb/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dlcdb.core.context_processors.branding',
                'dlcdb.lending.context_processors.lending_configuration',
            ],
        },
    },
]

WSGI_APPLICATION = 'dlcdb.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(DB_DIR / 'db.sqlite3'),
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',  # Docker notation: 'memcached:11211', see docker-compose
    },
    'select2': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'Europe/Berlin'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# https://docs.djangoproject.com/en/4.0/topics/i18n/formatting/#creating-custom-format-files
FORMAT_MODULE_PATH = [
    'dlcdb.core.formats',
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATICFILES_DIRS = [str(BASE_DIR / "dlcdb/static")]
STATIC_ROOT = str(STATICFILES_DIR)
STATIC_URL = '/static/'

MEDIA_ROOT = str(MEDIA_DIR)
MEDIA_URL = '/media/'

SAP_LIST_COMPARISON_RESULT_FOLDER = 'sap_list_comparison_results'

LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin/'

DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000  # default is: 1000

SITE_ID = 1

# https://docs.djangoproject.com/en/3.0/ref/clickjacking/#setting-x-frame-options-for-all-responses
X_FRAME_OPTIONS = 'SAMEORIGIN'

SELECT2_CACHE_BACKEND = 'select2'

MAX_FUTURE_LENT_DESIRED_END_DATE = '2099-12-31'

CRISPY_TEMPLATE_PACK = 'bootstrap3'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # 'rest_framework.permissions.IsAdminUser',
        'rest_framework.permissions.IsAuthenticated',
        # 'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    # 'PAGE_SIZE': 10,
}

# https://django-simple-history.readthedocs.io/en/latest/admin.html#disabling-the-option-to-revert-an-object
SIMPLE_HISTORY_REVERT_DISABLED=True
SIMPLE_HISTORY_FILEFIELD_TO_CHARFIELD = True


HUEY = SqliteHuey(
    name="dlcdb_huey",
    filename=str(DB_DIR / 'huey_task_queue.sqlite3'),
)


# TODO: Delete Verwaltung Device Types etc.
VERWALTUNG_DEVICE_TYPES = [
    'Tisch',
    'Stuhl',
    'Bett',
    'Drehstuhl',
    'Lampe',
    'Stehleuchte',
    'Schrank',
    'Regal',
    'Aktenvernichter',
    'Bücherwagen',
    'Container',
    'Bücher',
    'Zeitschriften',
    'Sonstiges',
]

VERWALTUNG_DEVICE_TYPES_ALIASES = {
    'Tisch': [],
    'Stuhl': ['Stühle', 'Stuehle'],
    'Drehstuhl': ['Drehstühle', 'Drehstuehle'],
    'Lampe/Stehleuchte': [],
    'Schrank': ['Schränke', 'Schraenke'],
    'Regal': [],
    'Aktenvernichter': [],
    'Bücherwagen': ['Buecherwagen', 'Bücherwägen', 'Buecherwaegen'],
    'Container': [],
    'Bücher/Zeitschriften': ['Buch', 'Buecher', 'Zeitschriften', 'Zeitschrift'],
    'Sonstiges': []
}


# Inventory/Scanner

# QRCODE_PREFIX (string) is used to prefix all generated uuids in qr codes
# in order to let the scanner deceide if a scanned qr code should be handled by
# this application. 
# 
# DO NOT CHANGE THIS PREFIX MID-PROJECT AS IT WILL BREAK THE SCANNER RECOGNIZING
# ALREADY PRINTED QR CODES.
QRCODE_DIR = 'qrcode'
QRCODE_PREFIX = 'DLCDB'
QRCODE_INFIXES = {
    'room': 'R',
    'device': 'D',
}

EMAIL_SUBJECT_PREFIX = env('EMAIL_SUBJECT_PREFIX')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

UDB_JSON_URL = env('UDB_JSON_URL')
# UDB_JSON_URL = "file://{}/temp/udb.json".format(settings.BASE_DIR)

PERSON_IMAGE_UPLOAD_DIR = "person_images"

# Branding
# Place your organization/insitution logos at the following paths to
# get rid of the default ACME logo.
logo_path = BASE_DIR / "dlcdb/static/dlcdb/branding/logo.svg"
logo_bw_path = BASE_DIR / "dlcdb/static/dlcdb/branding/logo_bw.svg"

BRANDING = {
    "BRANDING_ORG_NAME": env("BRANDING_ORG_NAME", default="ACME Corporation"),
    "BRANDING_ORG_ABBR": env("BRANDING_ORG_ABBR", default="ACME"),
    "BRANDING_ORG_STREET": env("BRANDING_ORG_STREET", default="Musterstrasse 123"),
    "BRANDING_ORG_ZIP_CITY": env("BRANDING_ORG_ZIP_CITY", default="D-98765 Musterstadt"), 
    "BRANDING_ORG_URL": env("BRANDING_ORG_URL", default="https://acme.de"),
    "BRANDING_IT_DEPT_NAME": env("BRANDING_IT_DEPT_NAME", default="IT-Support"),
    "BRANDING_IT_DEPT_PHONE": env("BRANDING_IT_DEPT_PHONE", default="+49 (0)123-456789"),
    "BRANDING_IT_DEPT_MAIL": env("BRANDING_IT_DEPT_MAIL", default="it-support@fqdn"),
    "BRANDING_LOGO": 'dlcdb/branding/logo.svg' if logo_path.exists() else 'dlcdb/branding/logo_acme.svg',
    "BRANDING_LOGO_BW": 'dlcdb/branding/logo_bw.svg' if logo_bw_path.exists() else 'dlcdb/branding/logo_acme_bw.svg',
}
