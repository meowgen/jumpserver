from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save


class AuditsConfig(AppConfig):
    name = 'audits'
    verbose_name = _('Audits')

    def ready(self):
        from . import signal_handlers
        if settings.SYSLOG_ENABLE:
            post_save.connect(signal_handlers.on_audits_log_create)
