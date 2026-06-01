from .models import TorneoConfig


def torneo(request):
    return {'torneo': TorneoConfig.get()}
