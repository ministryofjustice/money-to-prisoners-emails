from functools import partial
import os
from os.path import abspath, dirname, join
import sys
from urllib.parse import urljoin

BASE_DIR = dirname(dirname(abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

get_project_dir = partial(join, BASE_DIR)

APP = 'emails'
ENVIRONMENT = os.environ.get('ENV', 'local')
APP_BUILD_DATE = os.environ.get('APP_BUILD_DATE')
APP_BUILD_TAG = os.environ.get('APP_BUILD_TAG')
APP_GIT_COMMIT = os.environ.get('APP_GIT_COMMIT')
MOJ_INTERNAL_SITE = False

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or 'CHANGE_ME'
ALLOWED_HOSTS = ['*']

START_PAGE_URL = os.environ.get('START_PAGE_URL', 'https://www.gov.uk/send-prisoner-money')
CASHBOOK_URL = (
    f'https://{os.environ["PUBLIC_CASHBOOK_HOST"]}'
    if os.environ.get('PUBLIC_CASHBOOK_HOST')
    else 'http://localhost:8001'
)
BANK_ADMIN_URL = (
    f'https://{os.environ["PUBLIC_BANK_ADMIN_HOST"]}'
    if os.environ.get('PUBLIC_BANK_ADMIN_HOST')
    else 'http://localhost:8002'
)
NOMS_OPS_URL = (
    f'https://{os.environ["PUBLIC_NOMS_OPS_HOST"]}'
    if os.environ.get('PUBLIC_NOMS_OPS_HOST')
    else 'http://localhost:8003'
)
SEND_MONEY_URL = (
    f'https://{os.environ["PUBLIC_SEND_MONEY_HOST"]}'
    if os.environ.get('PUBLIC_SEND_MONEY_HOST')
    else 'http://localhost:8004'
)
EMAILS_URL = (
    f'https://{os.environ["PUBLIC_EMAILS_HOST"]}'
    if os.environ.get('PUBLIC_EMAILS_HOST')
    else 'http://localhost:8006'
)
SITE_URL = EMAILS_URL

# Application definition
INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.contenttypes',
    'django.contrib.auth',
)
PROJECT_APPS = (
    'mtp_common',
    'mtp_common.metrics',
    'downloads',
    'callbacks',
)
INSTALLED_APPS += PROJECT_APPS


WSGI_APPLICATION = 'mtp_emails.wsgi.application'
ROOT_URLCONF = 'mtp_emails.urls'
MIDDLEWARE = (
    'mtp_common.metrics.middleware.RequestMetricsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'mtp_common.auth.csrf.CsrfViewMiddleware',
    'mtp_common.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'mtp_common.analytics.ReferrerPolicyMiddleware',
)

APPLICATIONINSIGHTS_CONNECTION_STRING = os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')
if APPLICATIONINSIGHTS_CONNECTION_STRING:
    from mtp_common.application_insights import AppInsightsTraceExporter
    from opencensus.trace.samplers import ProbabilitySampler

    # Sends traces to Azure Application Insights
    MIDDLEWARE += ('opencensus.ext.django.middleware.OpencensusMiddleware',)
    OPENCENSUS = {
        'TRACE': {
            'SAMPLER': ProbabilitySampler(rate=0.1 if ENVIRONMENT == 'prod' else 1),
            'EXPORTER': AppInsightsTraceExporter(),
        }
    }

HEALTHCHECKS = []
AUTODISCOVER_HEALTHCHECKS = True

METRICS_USER = os.environ.get('METRICS_USER', 'prom')
METRICS_PASS = os.environ.get('METRICS_PASS', 'prom')

# security tightening
# some overridden in prod/docker settings where SSL is ensured
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = False
CSRF_FAILURE_VIEW = 'mtp_common.auth.csrf.csrf_failure'


# Data stores
DATABASES = {}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'mtp',
    }
}


# Internationalization
LANGUAGE_CODE = 'en-gb'
LANGUAGES = (
    ('en-gb', 'English'),
    ('cy', 'Cymraeg'),
)
LOCALE_PATHS = (get_project_dir('translations'),)
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True
FORMAT_MODULE_PATH = ['mtp_emails.settings.formats']


# Static files (CSS, JavaScript, Images)
STATIC_ROOT = 'static'
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    get_project_dir('assets'),
    get_project_dir('assets-static'),
]
PUBLIC_STATIC_URL = urljoin(SEND_MONEY_URL, STATIC_URL)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            get_project_dir('templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'mtp_common.context_processors.analytics',
                'mtp_common.context_processors.app_environment',
                'mtp_common.context_processors.govuk_localisation',
            ],
        },
    },
]

# logging settings
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
        },
        'elk': {
            '()': 'mtp_common.logging.ELKFormatter'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple' if ENVIRONMENT == 'local' else 'elk',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'root': {
        'level': 'WARNING',
        'handlers': ['console'],
    },
    'loggers': {
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        },
        'mtp': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}
if APPLICATIONINSIGHTS_CONNECTION_STRING:
    # Sends messages from `mtp` logger to Azure Application Insights
    LOGGING['handlers']['azure'] = {
        'level': 'INFO',
        'class': 'mtp_common.application_insights.AppInsightsLogHandler',
    }
    LOGGING['loggers']['mtp']['handlers'].append('azure')
    LOGGING['root']['handlers'].append('azure')

# sentry exception handling
if os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=os.environ['SENTRY_DSN'],
        integrations=[DjangoIntegration()],
        environment=ENVIRONMENT,
        release=APP_GIT_COMMIT or 'unknown',
        send_default_pii=DEBUG,
        max_request_body_size='medium' if DEBUG else 'never',
    )

TEST_RUNNER = 'mtp_common.test_utils.runner.TestRunner'

# authentication
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
AUTHENTICATION_BACKENDS = (
    'mtp_common.auth.backends.MojBackend',
)


# control the time a session exists for; should match api's access token expiry
SESSION_COOKIE_AGE = 60 * 60  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True


# API_CLIENT_ID = 'emails'
# API_CLIENT_SECRET = os.environ.get('API_CLIENT_SECRET', 'emails')
API_URL = os.environ.get('API_URL', 'http://localhost:8000')

# LOGIN_URL = 'login'
# LOGIN_REDIRECT_URL = 'bank_admin:dashboard'
# LOGOUT_URL = 'logout'

OAUTHLIB_INSECURE_TRANSPORT = True

ANALYTICS_REQUIRED = os.environ.get('ANALYTICS_REQUIRED', 'False') == 'True'
GA4_MEASUREMENT_ID = os.environ.get('GA4_MEASUREMENT_ID', None)

REQUEST_PAGE_SIZE = 500

ZENDESK_BASE_URL = 'https://ministryofjustice.zendesk.com'
ZENDESK_API_USERNAME = os.environ.get('ZENDESK_API_USERNAME', '')
ZENDESK_API_TOKEN = os.environ.get('ZENDESK_API_TOKEN', '')
ZENDESK_REQUESTER_ID = os.environ.get('ZENDESK_REQUESTER_ID', '')
ZENDESK_GROUP_ID = 26417927
ZENDESK_CUSTOM_FIELDS = {
    'referer': 26047167,
    'username': 29241738,
    'user_agent': 23791776,
    'contact_email': 30769508,
}

GOVUK_NOTIFY_API_KEY = os.environ.get('GOVUK_NOTIFY_API_KEY', '')
GOVUK_NOTIFY_REPLY_TO_PUBLIC = os.environ.get('GOVUK_NOTIFY_REPLY_TO_PUBLIC', '')
GOVUK_NOTIFY_REPLY_TO_STAFF = os.environ.get('GOVUK_NOTIFY_REPLY_TO_STAFF', '')
GOVUK_NOTIFY_BLOCKED_DOMAINS = set(os.environ.get('GOVUK_NOTIFY_BLOCKED_DOMAINS', '').split())
# install GOV.UK Notify fallback for emails accidentally sent using Django's email functionality:
EMAIL_BACKEND = 'mtp_common.notify.email_backend.NotifyEmailBackend'

GOVUK_NOTIFY_CALLBACKS_BEARER_TOKEN = os.environ.get('GOVUK_NOTIFY_CALLBACKS_BEARER_TOKEN', 'CHANGE_ME')

SHOW_LANGUAGE_SWITCH = os.environ.get('SHOW_LANGUAGE_SWITCH', 'False') == 'True'

try:
    from .local import *  # noqa
except ImportError:
    pass
