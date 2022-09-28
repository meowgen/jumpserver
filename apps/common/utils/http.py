# -*- coding: utf-8 -*-
#
import time
from email.utils import formatdate
import calendar
import threading

_STRPTIME_LOCK = threading.Lock()

_GMT_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"
_ISO8601_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


def to_unixtime(time_string, format_string):
    time_string = time_string.decode("ascii")
    with _STRPTIME_LOCK:
        return int(calendar.timegm(time.strptime(time_string, format_string)))


def http_date(timeval=None):
    """Возвращает строку времени по Гринвичу, соответствующую стандарту HTTP, которая выражается в формате strftime как "%a, %d %b %Y %H:%M:%S GMT".
     Но strftime использовать нельзя, потому что результат strftime зависит от локали."""
    return formatdate(timeval, usegmt=True)


def http_to_unixtime(time_string):
    """Преобразует строку в формате даты HTTP во время UNIX (секунды с 1 января 1970 года в полночь UTC).
     Формат даты: «Sat, 05 Dec 2015 11:10:29 GMT».
     """
    return to_unixtime(time_string, _GMT_FORMAT)


def iso8601_to_unixtime(time_string):
    """Преобразование строки времени ISO8601 (например, 2012-02-24T06:07:48.000Z) во время UNIX с точностью до секунд"""
    return to_unixtime(time_string, _ISO8601_FORMAT)
