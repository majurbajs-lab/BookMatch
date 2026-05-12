from django.apps import AppConfig


class ReadingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reading'
    verbose_name = 'Bralna evidenca'

    def ready(self):
        import reading.signals  # noqa
