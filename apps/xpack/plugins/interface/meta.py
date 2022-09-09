# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _
from django.urls import reverse_lazy

from xpack import const

META = {
    "verbose_name": _("Interface settings"),
    "endpoint": reverse_lazy("xpack:interface:interface"),
    "permission": const.PERMISSION_SUPER_ADMIN,
}
