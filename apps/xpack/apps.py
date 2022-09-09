from django.apps import AppConfig

from django.utils.translation import ugettext_lazy as _


class XpackConfig(AppConfig):
    name = 'xpack'
    verbose_name = _('XPACK')

    def ready(self):
        from . import signal_handlers
        super().ready()
