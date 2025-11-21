"""
Docker-specific Django settings for microsprings_inventory_system project.
"""

import os
from .settings import *

# Override settings for Docker environment
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-docker-secret-key-change-in-production')

# Allowed hosts
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Database configuration (MySQL - Remote Server)
# Database settings are loaded from environment variables via settings.py
# Ensure these are set in .env.production:
# DATABASE_ENGINE, DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_PORT
# The base settings.py will handle MySQL configuration automatically

# CORS settings
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS', 
    'http://localhost:3000,http://127.0.0.1:3000'
).split(',')

# Static files configuration for Docker
STATIC_URL = '/static/'
STATIC_ROOT = '/app/staticfiles'

# Additional static files directories (only add if directory exists)
STATICFILES_DIRS = []

# Static files finders (ensure Django can find admin static files)
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Logging for Docker
# Create logs directory if it doesn't exist
import os
from pathlib import Path

# Determine if we're running in Docker or locally
if os.path.exists('/app'):
    # Running in Docker
    log_dir = '/app/logs'
    log_file = '/app/logs/msp_erp.log'
else:
    # Running locally
    log_dir = BASE_DIR / 'logs'
    log_file = BASE_DIR / 'logs' / 'msp_erp.log'

os.makedirs(log_dir, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': log_file,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'authentication': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'manufacturing': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Cache configuration for Docker (use Redis in production)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
