from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES['default']['NAME'] = 'mipolla'
DATABASES['default']['USER'] = 'mipolla'
DATABASES['default']['PASSWORD'] = 'mipolla123'
DATABASES['default']['HOST'] = config('DB_HOST', default='localhost')
DATABASES['default']['PORT'] = config('DB_PORT', default='5432')

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Nunca enviar correos reales en local — solo imprimir en consola
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
