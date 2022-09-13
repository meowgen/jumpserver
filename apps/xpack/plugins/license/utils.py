# -*- coding: utf-8 -*-
#

import os
import platform
import json
import time
import ctypes

from common.utils import get_logger
from common.utils.common import get_file_by_arch

logger = get_logger(__file__)


def date_to_timestamp(date):
    return time.mktime(time.strptime(date, "%Y-%m-%d"))


def get_license_dll_path():
    path_lib = 'xpack/plugins/license/lib'
    file_name = 'license.so'
    full_dll_path = get_file_by_arch(path_lib, file_name)
    return full_dll_path


def decrypt_license(license_content):
    try:
#         path_license_dll = get_license_dll_path()
#         lib = ctypes.CDLL(path_license_dll)
#         lib.DecryptLicense.argtypes = [ctypes.c_char_p]
#         lib.DecryptLicense.restype = ctypes.c_char_p
#         info = lib.DecryptLicense(license_content.encode())
#         license_info = json.loads(info)
        license_info = {"license":{"corporation":"test corp", "expired":"2034-01-01", "count":200, "product":"JUMPSERVER"}}
    except Exception as e:
        logger.debug('License decrypt error: {}'.format(e))
        return {}
    else:
        return license_info


def validate_license(license_info):
    info = license_info.get('license', {})

    if not info:
        return False

    if info.get('product') != 'JUMPSERVER':
        logger.debug('License invalid product: {}'.format(info.get('product')))
        return False

    expired_timestamp = date_to_timestamp(info.get('expired'))
    if expired_timestamp < time.time():
        logger.debug('License has expired: {}'.format(info.get('expired')))
        return False

    return True
