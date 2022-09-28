#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

"""
Совместимая версия Python
"""

import sys

is_py2 = (sys.version_info[0] == 2)
is_py3 = (sys.version_info[0] == 3)


try:
    import simplejson as json
except (ImportError, SyntaxError):
    import json


if is_py2:

    def to_bytes(data):
        if isinstance(data, unicode):
            return data.encode('utf-8')
        else:
            return data

    def to_string(data):
        return to_bytes(data)

    def to_unicode(data):
        if isinstance(data, bytes):
            return data.decode('utf-8')
        else:
            return data

    def stringify(input):
        if isinstance(input, dict):
            return dict([(stringify(key), stringify(value)) for key,value in input.iteritems()])
        elif isinstance(input, list):
            return [stringify(element) for element in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input

    builtin_str = str
    bytes = str
    str = unicode


elif is_py3:

    def to_bytes(data):
        if isinstance(data, str):
            return data.encode(encoding='utf-8')
        else:
            return data

    def to_string(data):
        if isinstance(data, bytes):
            return data.decode('utf-8')
        else:
            return data

    def to_unicode(data):
        return to_string(data)

    def stringify(input):
        return input

    builtin_str = str
    bytes = bytes
    str = str

