# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _
from django.urls import reverse_lazy
from xpack import const

META = {
    "verbose_name": _("Cloud center"),
    "endpoint": reverse_lazy("xpack:cloud:account-list"),
    "permission": const.PERMISSION_ORG_ADMIN,
}
