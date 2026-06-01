from .base import *

DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

CSRF_TRUSTED_ORIGINS = [
    'https://www.elcarguero.com',
    'https://elcarguero.com',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
FORCE_SCRIPT_NAME = '/MiPolla'

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Evolution API (WhatsApp) — direct container-to-container via shared Docker network
EVOLUTION_API_URL = 'http://elcarguero_evolution:8080'
EVOLUTION_API_KEY = 'superapikey'
EVOLUTION_INSTANCE = 'elcarguero'
