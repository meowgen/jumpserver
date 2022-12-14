# coding:utf-8
#

from django.urls import path, include
from django.db.transaction import non_atomic_requests

from .. import views
from users import views as users_view

app_name = 'authentication'

urlpatterns = [
    # login
    path('login/', non_atomic_requests(views.UserLoginView.as_view()), name='login'),
    path('login/mfa/', views.UserLoginMFAView.as_view(), name='login-mfa'),
    path('login/wait-confirm/', views.UserLoginWaitConfirmView.as_view(), name='login-wait-confirm'),
    path('login/guard/', views.UserLoginGuardView.as_view(), name='login-guard'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),

    # users
    path('password/forgot/', users_view.UserForgotPasswordView.as_view(), name='forgot-password'),
    path('password/reset/', users_view.UserResetPasswordView.as_view(), name='reset-password'),
    path('password/verify/', users_view.UserVerifyPasswordView.as_view(), name='user-verify-password'),

    # Profile
    path('profile/pubkey/generate/', users_view.UserPublicKeyGenerateView.as_view(), name='user-pubkey-generate'),
    path('profile/mfa/', users_view.MFASettingView.as_view(), name='user-mfa-setting'),

    # OTP Setting
    path('profile/otp/enable/start/', users_view.UserOtpEnableStartView.as_view(), name='user-otp-enable-start'),
    path('profile/otp/enable/install-app/', users_view.UserOtpEnableInstallAppView.as_view(),
         name='user-otp-enable-install-app'),
    path('profile/otp/enable/bind/', users_view.UserOtpEnableBindView.as_view(), name='user-otp-enable-bind'),
    path('profile/otp/disable/', users_view.UserOtpDisableView.as_view(),
         name='user-otp-disable'),

    # openid
    path('cas/', include(('authentication.backends.cas.urls', 'authentication'), namespace='cas')),
    path('openid/', include(('authentication.backends.oidc.urls', 'authentication'), namespace='openid')),
    path('saml2/', include(('authentication.backends.saml2.urls', 'authentication'), namespace='saml2')),
    path('captcha/', include('captcha.urls')),
]
