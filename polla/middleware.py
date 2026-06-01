from django.conf import settings
from django.urls import set_script_prefix


class ScriptNameMiddleware:
    """
    Ensures reverse() generates URLs with the correct subpath prefix
    when deployed at /MiPolla/ (or any FORCE_SCRIPT_NAME value).
    """
    def __init__(self, get_response):
        self.get_response = get_response
        prefix = getattr(settings, 'FORCE_SCRIPT_NAME', None) or ''
        set_script_prefix(prefix)

    def __call__(self, request):
        return self.get_response(request)
