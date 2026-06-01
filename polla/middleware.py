from django.conf import settings
from django.urls import set_script_prefix


class ScriptNameMiddleware:
    """
    Ensures reverse() generates URLs with the correct subpath prefix
    when deployed at a sub-URL (FORCE_SCRIPT_NAME). Must run per-request
    since Gunicorn workers don't share thread-locals.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        prefix = getattr(settings, 'FORCE_SCRIPT_NAME', None) or ''
        set_script_prefix(prefix)
        return self.get_response(request)
