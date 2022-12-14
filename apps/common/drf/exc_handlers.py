from django.core.exceptions import PermissionDenied, ObjectDoesNotExist as DJObjectDoesNotExist
from django.http import Http404
from django.utils.translation import gettext
from django.db.models.deletion import ProtectedError
from rest_framework import exceptions
from rest_framework.views import set_rollback
from rest_framework.response import Response

from common.exceptions import JMSObjectDoesNotExist, ReferencedByOthers
from logging import getLogger

logger = getLogger('drf_exception')
unexpected_exception_logger = getLogger('unexpected_exception')


def extract_object_name(exc, index=0):
    if exc.args:
        (msg, *others) = exc.args
    else:
        return gettext('Object')
    return gettext(msg.split(sep=' ', maxsplit=index + 1)[index])


def common_exception_handler(exc, context):
    logger.exception('')

    if isinstance(exc, Http404):
        exc = JMSObjectDoesNotExist(object_name=extract_object_name(exc, 1))
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, DJObjectDoesNotExist):
        exc = JMSObjectDoesNotExist(object_name=extract_object_name(exc, 0))
    elif isinstance(exc, ProtectedError):
        exc = ReferencedByOthers()

    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        if isinstance(exc.detail, str) and isinstance(exc.get_codes(), str):
            data = {'detail': exc.detail, 'code': exc.get_codes()}
        else:
            data = exc.detail

        set_rollback()
        return Response(data, status=exc.status_code, headers=headers)
    else:
        unexpected_exception_logger.exception('')

    return None
