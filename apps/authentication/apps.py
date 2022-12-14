from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuthenticationConfig(AppConfig):
    name = 'authentication'
    verbose_name = _('Authentication')

    def ready(self):
        from . import signal_handlers
        from . import notifications
        super().ready()

