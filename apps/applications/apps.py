from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _
from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    name = 'applications'
    verbose_name = _('Applications')
