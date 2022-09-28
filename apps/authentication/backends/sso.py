from django.conf import settings

from .base import JMSModelBackend


class SSOAuthentication(JMSModelBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_SSO

    def authenticate(self, request, sso_token=None, **kwargs):
        pass

class AuthorizationTokenAuthentication(JMSModelBackend):
    def authenticate(self, request, **kwargs):
        pass
