from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException


class SSOAuthClosed(JMSException):
    default_code = 'sso_auth_closed'
    default_detail = _('SSO auth closed')

class PasswordInvalid(JMSException):
    default_code = 'passwd_invalid'
    default_detail = _('Your password is invalid')
