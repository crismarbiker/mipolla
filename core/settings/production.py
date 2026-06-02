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

# Static/media URLs must include the subpath prefix so {% static %} generates correct URLs
# Without this, /static/css/polla.css → 404 (hits elcarguero frontend, not MiPolla)
STATIC_URL = '/MiPolla/static/'
MEDIA_URL  = '/MiPolla/media/'

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Evolution API (WhatsApp) — leídos del .env del servidor
EVOLUTION_API_URL  = config('EVOLUTION_API_URL',  default='http://elcarguero_evolution:8080')
EVOLUTION_API_KEY  = config('EVOLUTION_API_KEY',  default='')
EVOLUTION_INSTANCE = config('EVOLUTION_INSTANCE', default='elcarguero')
APP_URL            = config('APP_URL', default='https://www.elcarguero.com/MiPolla/')
