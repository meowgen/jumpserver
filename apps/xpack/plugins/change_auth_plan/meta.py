# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _
from django.urls import reverse_lazy
from xpack import const

META = {
    "verbose_name": _("Change auth plan"),
    "endpoint": reverse_lazy("xpack:change_auth_plan:plan-list"),
    "permission": const.PERMISSION_ORG_ADMIN,
}
