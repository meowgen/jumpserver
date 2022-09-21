import time
import hmac
import base64

from common.utils import get_logger
from common.sdk.im.utils import digest, as_request
from common.sdk.im.mixin import BaseRequest

logger = get_logger(__file__)


def sign(secret, data):

    digest = hmac.HMAC(
        key=secret.encode('utf8'),
        msg=data.encode('utf8'),
        digestmod=hmac._hashlib.sha256
    ).digest()
    signature = base64.standard_b64encode(digest).decode('utf8')
    # signature = urllib.parse.quote(signature, safe='')
    # signature = signature.replace('+', '%20').replace('*', '%2A').replace('~', '%7E').replace('/', '%2F')
    return signature


class ErrorCode:
    INVALID_TOKEN = 88
