from django.apps import AppConfig


class LoansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'loans'
    verbose_name = 'Izposoja knjig'

    def ready(self):
        import loans.signals  # noqa
