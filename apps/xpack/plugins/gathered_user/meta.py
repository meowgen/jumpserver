# -*- coding: utf-8 -*-
#

from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from xpack import const


META = {
    "verbose_name": _("Gathered user"),
    "endpoint": reverse_lazy("xpack:gathered_user:gathered-user-list"),
    "permission": const.PERMISSION_ORG_ADMIN,
}
