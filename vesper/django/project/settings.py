"""
Django settings for Vesper project.

Generated by 'django-admin startproject' using Django 2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""


import logging
import os

from vesper.archive_settings import archive_settings
from vesper.archive_paths import archive_paths


def _configure_logging():

    """Configures the root logger message format."""

    # We put the time of a log message first for sorting purposes (in
    # case sorting is ever needed). We put the message last so a log line
    # can be split into its parts relatively easily, even if the message
    # happens to contain one or more separators. We put the level name
    # just before the message since that reads nicely.
    separator = ' | '
    format = separator.join((
        '%(asctime)s.%(msecs)03d', '%(name)s', '%(levelname)s', '%(message)s'))
    logging.basicConfig(format=format, datefmt='%Y-%m-%d %H:%M:%S')


# TODO: Is there a better place for this? We want to run it just once,
# as early as possible when our Django project starts.
_configure_logging()


# Set this `True` to omit UI and URLs that support archive modification,
# including Django admin and login views.
ARCHIVE_READ_ONLY = False


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'fi1dxvoed!-l9y-e7-2_m^l_if8qp2lixmggj&lk6(ad)4f+9g'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Set this to `True` to include the Django debug toolbar (see
# https://django-debug-toolbar.readthedocs.io/en/stable).
INCLUDE_DJANGO_DEBUG_TOOLBAR = False

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'vesper.django.app.apps.VesperConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# Django Debug Toolbar
# See https://django-debug-toolbar.readthedocs.io/en/stable/installation.html.

if INCLUDE_DJANGO_DEBUG_TOOLBAR:
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE = \
        ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INTERNAL_IPS = ['127.0.0.1']
    

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

WSGI_APPLICATION = 'vesper.django.project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

# TODO: Switch to BigAutoField when Vesper database tables will change
# for some other reason. We don't want to force users to migrate their
# databases just for this. There's no hurry, since it is unlikely that
# any archive database table will exhaust 2**32 IDs anytime soon.
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'


def _create_databases_setting_value():
    
    db = archive_settings.database
    
    if db.engine == 'SQLite':
        
        value = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(archive_paths.sqlite_database_file_path)
        }
        
    elif db.engine == 'PostgreSQL':
        
        value = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db.name,
            'USER': db.user,
            'PASSWORD': db.password,
            'HOST': db.host,
            'PORT': db.port
        }
        
    else:
        raise ValueError(
            'Unrecognized database engine "{}".'.format(db.engine))
        
    return {'default': value}


DATABASES = _create_databases_setting_value()


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'US/Eastern'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
STATIC_URL = '/static/'


# Directory to which the static files of all of the Django apps of this
# project are copied by "python manage.py collectstatic". Static files
# are served from this directory when Vesper is deployed on nginx/uWSGI,
# but not when it is deployed on the Django development server.
STATIC_ROOT = '/opt/vesper/static'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
