from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Uporabniški računi'

    def ready(self):
        # Registriraj signale, ki samodejno ustvarijo Profile ob registraciji
        import accounts.signals  # noqa: F401
