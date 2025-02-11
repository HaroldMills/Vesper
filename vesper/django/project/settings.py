"""
Django settings for Vesper project.

Most recently updated according to a settings file generated by
'django-admin startproject' using Django 5.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""


# TODO: For Vesper 0.5.0, which will require that the Vesper server run
# in a Docker container:
# * Drop support for "Archive Settings.yaml" (changes will be to apps.py).
# * Drop support for "Environment Variables.env".
# * Set ARCHIVE_DIR_PATH to `'/Archive'`.
# * Provide no default value for VESPER_DJANGO_SECRET_KEY.
# * Change DEBUG default value to `False`.


from pathlib import Path

from environs import Env

import vesper.util.logging_utils as logging_utils


# TODO: Set server-wide logging level here. The logging level is currently
# hard-coded to `logging.INFO` in various places in the server code.


# Configure logging for Vesper server early, before anybody logs anything.
logging_utils.configure_root_logger()


# Read .env file and environment variables.
env = Env()
env.read_env('Environment Variables.env', recurse=False)


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: Never put an actual secret key here.
SECRET_KEY = env(
    'VESPER_DJANGO_SECRET_KEY',
    'YKs482x7HnCKx1a7PvSf5zkRbvvn6nKRp6QSgiXjDLQg8_XPDPaoiw')

# SECURITY WARNING: Don't run with debug turned on in production.
DEBUG = env.bool('VESPER_DJANGO_DEBUG', True)

ALLOWED_HOSTS = env.list(
    'VESPER_DJANGO_ALLOWED_HOSTS',
    ['.localhost', '127.0.0.1', '[::1]'], subcast=str)

# For using Vesper with a URL base other than just "/", e.g. at
# "/project-name/archive-name/" behind an NGINX reverse proxy.
# Note that `VESPER_URL_BASE` should start and end with a slash.
VESPER_URL_BASE = env('VESPER_URL_BASE', '/')
FORCE_SCRIPT_NAME = VESPER_URL_BASE
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'vesper.django.app.apps.VesperConfig',
    'vesper.django.old_bird.apps.OldBirdConfig'
    # 'vesper.django.s3_clip_tests.apps.S3ClipTestsConfig',
]

MIDDLEWARE = [
    'vesper.django.app.middleware.healthCheckMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vesper.django.project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'vesper.django.project.asgi.application'
# WSGI_APPLICATION = 'vesper.django.project.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = VESPER_URL_BASE + 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles/'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    }
}
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

# TODO: Switch to BigAutoField when Vesper database tables will change
# for some other reason. We don't want to force users to migrate their
# databases just for this. There's no hurry, since it is unlikely that
# any archive database table will exhaust 2**32 IDs anytime soon.
# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'


LOGIN_URL = VESPER_URL_BASE + 'login/'
LOGIN_REDIRECT_URL = VESPER_URL_BASE
LOGOUT_REDIRECT_URL = VESPER_URL_BASE


# The path of the Vesper archive directory. We define this attribute
# here instead of at the end of this file so we can use it in the
# default database URL, below.
container_archive_dir_path = Path('/Archive')
if container_archive_dir_path.is_dir():
    VESPER_ARCHIVE_DIR_PATH = container_archive_dir_path
else:
    VESPER_ARCHIVE_DIR_PATH = Path.cwd()


# The URL of the Vesper archive database, by default the URL of the
# SQLite database in the file "Archive Database.sqlite" of the Vesper
# archive directory.
#
# See https://github.com/jazzband/dj-database-url for the form of
# URLs for various kinds of databases.
VESPER_ARCHIVE_DATABASE_URL = env.dj_db_url(
    'VESPER_ARCHIVE_DATABASE_URL',
    f'sqlite:///{VESPER_ARCHIVE_DIR_PATH}/Archive Database.sqlite')


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
DATABASES = {
    'default': VESPER_ARCHIVE_DATABASE_URL
}


VESPER_ARCHIVE_READ_ONLY = env.bool('VESPER_ARCHIVE_READ_ONLY', False)

VESPER_PRESETS_STATIC = env.bool('VESPER_PRESETS_STATIC', True)

VESPER_PREFERENCES_STATIC = env.bool('VESPER_PREFERENCES_STATIC', True)

VESPER_ADMIN_URL_PATTERN = env('VESPER_ADMIN_URL_PATTERN', 'admin/')

# The `VESPER_INCLUDE_PROCESSORS` setting controls whether or not the
# Vesper server includes detector and classifier extensions. Set it to
# `True` when building the full `vesper` Python package, and to `False`
# when building the `vesper-slim` package. (Also be sure to comment out
# or uncomment the relevant dependencies in the `pyproject.toml` file.)
# Excluding detector and classifier extensions speeds server startup
# considerably, mainly because the server no longer needs to import
# TensorFlow. Excluding unneeded detector and classifier dependencies
# (most importantly TensorFlow) from the `vesper-slim` package also
# makes that package much smaller than the full `vesper` package.
#
# Detectors and classifiers will move from the Vesper core server
# to auxiliary Vesper processing servers in the future, which may
# obviate this setting.
VESPER_INCLUDE_PROCESSORS = False
