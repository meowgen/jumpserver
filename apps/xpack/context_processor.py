# -*- coding: utf-8 -*-
#

from .utils import get_permed_plugins


def xpack_processor(request):
    context = {
        'XPACK_PLUGINS': get_permed_plugins(request.user),
        'XPACK_ENABLED': True
    }
    return context


