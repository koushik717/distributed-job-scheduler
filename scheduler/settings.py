"""
Django settings for the Distributed Async Job Scheduler.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'dev-insecure-key-change-in-production-xk3j2m1n5v8b9c0d'
)

DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

ALLOWED_HOSTS = ['*']

# ─── Installed Apps ─────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    'django_filters',
    # Project apps
    'jobs',
    'metrics',
]

# ─── Middleware ──────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'scheduler.urls'

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

WSGI_APPLICATION = 'scheduler.wsgi.application'

# ─── Database (PostgreSQL = Source of Truth) ─────────────────
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgres://scheduler:scheduler_pass@localhost:5432/scheduler_db'
)

# Parse DATABASE_URL
import re
db_match = re.match(
    r'postgres://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>\d+)/(?P<name>.+)',
    DATABASE_URL
)

if db_match:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_match.group('name'),
            'USER': db_match.group('user'),
            'PASSWORD': db_match.group('password'),
            'HOST': db_match.group('host'),
            'PORT': db_match.group('port'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ─── Celery Configuration ───────────────────────────────────
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Visibility timeout: if a worker doesn't ack within 30 min, task is re-delivered
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 1800,
}

# Task queue routing
CELERY_TASK_QUEUES = {
    'high_priority': {
        'exchange': 'high_priority',
        'routing_key': 'high_priority',
    },
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'low_priority': {
        'exchange': 'low_priority',
        'routing_key': 'low_priority',
    },
}

CELERY_TASK_DEFAULT_QUEUE = 'default'

# ─── Redis ───────────────────────────────────────────────────
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# ─── REST Framework ─────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# ─── CORS ────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ─── Logging (Structured JSON) ──────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.json.JsonFormatter',
            'fmt': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
        'verbose': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'json_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'jobs': {
            'handlers': ['json_console'],
            'level': 'INFO',
            'propagate': False,
        },
        'workers': {
            'handlers': ['json_console'],
            'level': 'INFO',
            'propagate': False,
        },
        'metrics': {
            'handlers': ['json_console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ─── Static Files ────────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Job Scheduler Config ────────────────────────────────────
JOB_TIMEOUT_SECONDS = 1800  # 30 minutes - mark stale RUNNING jobs as FAILED
JOB_STALE_CHECK_INTERVAL = 60  # Check for stale jobs every 60 seconds
