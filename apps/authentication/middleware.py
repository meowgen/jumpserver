import base64

from django.shortcuts import redirect, reverse
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django.conf import settings

from common.utils import gen_key_pair


class MFAMiddleware:
    """
    Это промежуточное программное обеспечение используется для глобального перехвата MFA с включенной, 
    но не прошедшей проверку подлинности, например, OIDC, CAS, входом в систему
     с использованием сторонней библиотеки, прямым входом в систему,
    Таким образом, его можно контролировать только в промежуточном программном обеспечении.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.session.get('auth_mfa_required'):
            return response
        if request.user.is_anonymous:
            return response

        white_urls = [
            'login/mfa', 'mfa/select', 'jsi18n/', '/static/',
            '/profile/otp', '/logout/',
        ]
        for url in white_urls:
            if request.path.find(url) > -1:
                return response

        if request.path.find('users/profile') > -1:
            return HttpResponse('', status=401)

        url = reverse('authentication:login-mfa') + '?_=middleware'
        return redirect(url)


class SessionCookieMiddleware(MiddlewareMixin):

    @staticmethod
    def set_cookie_public_key(request, response):
        if request.path.startswith('/api'):
            return
        pub_key_name = settings.SESSION_RSA_PUBLIC_KEY_NAME
        public_key = request.session.get(pub_key_name)
        cookie_key = request.COOKIES.get(pub_key_name)
        if public_key and public_key == cookie_key:
            return

        pri_key_name = settings.SESSION_RSA_PRIVATE_KEY_NAME
        private_key, public_key = gen_key_pair()
        public_key_decode = base64.b64encode(public_key.encode()).decode()
        request.session[pub_key_name] = public_key_decode
        request.session[pri_key_name] = private_key
        response.set_cookie(pub_key_name, public_key_decode)

    @staticmethod
    def set_cookie_session_prefix(request, response):
        key = settings.SESSION_COOKIE_NAME_PREFIX_KEY
        value = settings.SESSION_COOKIE_NAME_PREFIX
        if request.COOKIES.get(key) == value:
            return response
        response.set_cookie(key, value)

    @staticmethod
    def set_cookie_session_expire(request, response):
        if not request.session.get('auth_session_expiration_required'):
            return
        value = 'age'
        if settings.SESSION_EXPIRE_AT_BROWSER_CLOSE_FORCE or \
                not request.session.get('auto_login', False):
            value = 'close'

        age = request.session.get_expiry_age()
        response.set_cookie('jms_session_expire', value, max_age=age)
        request.session.pop('auth_session_expiration_required', None)

    def process_response(self, request, response: HttpResponse):
        self.set_cookie_session_prefix(request, response)
        self.set_cookie_public_key(request, response)
        self.set_cookie_session_expire(request, response)
        return response
