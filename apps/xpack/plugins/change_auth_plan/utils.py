# -*- coding: utf-8 -*-
#
from django.utils import timezone

from common.utils import get_logger

from . import const

logger = get_logger(__file__)


def format_date(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')


def get_now():
    return format_date(timezone.now().local_now())


def wrapper_error(err, wrapper='*' * 6 + ' ', new_line='\n'):
    return '\033[31m{wrapper}{new_line}{err}{new_line}{wrapper}\033[0m'.format(
        wrapper=wrapper, err=err, new_line=new_line
    )


def generate_random_password(**kwargs):
    import random
    import string
    length = int(kwargs.get('length', const.DEFAULT_PASSWORD_RULES['length']))
    symbol_set = kwargs.get('symbol_set')
    if symbol_set is None:
        symbol_set = const.DEFAULT_PASSWORD_RULES['symbol_set']
    chars = string.ascii_letters + string.digits + symbol_set
    password = ''.join([random.choice(chars) for _ in range(length)])
    return password
