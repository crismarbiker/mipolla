from django.apps import AppConfig


class PollaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'polla'
    verbose_name = 'Polla Mundial 2026'

    def ready(self):
        import polla.signals  # noqa
