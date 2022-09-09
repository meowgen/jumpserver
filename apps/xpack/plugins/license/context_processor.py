# -*- coding: utf-8 -*-
#

from .models import License


def license_processor(request):
    context = {}
    if License.has_valid_license():
        context.update({"LICENSE_VALID": "1"})
    return context
