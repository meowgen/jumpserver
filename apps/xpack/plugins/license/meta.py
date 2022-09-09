# -*- coding: utf-8 -*-
#

from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from xpack import const


META = {
    "verbose_name": _("License"),
    "endpoint": reverse_lazy("xpack:license:license-detail"),
    "permission": const.PERMISSION_SUPER_ADMIN,
}
