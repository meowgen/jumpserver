# coding:utf-8
#
from django.urls import path
from rest_framework.routers import DefaultRouter

from .. import api

app_name = 'authentication'
router = DefaultRouter()
router.register('access-keys', api.AccessKeyViewSet, 'access-key')
router.register('sso', api.SSOViewSet, 'sso')
router.register('temp-tokens', api.TempTokenViewSet, 'temp-token')
router.register('connection-token', api.ConnectionTokenViewSet, 'connection-token')
router.register('super-connection-token', api.SuperConnectionTokenViewSet, 'super-connection-token')


urlpatterns = [
    path('auth/', api.TokenCreateApi.as_view(), name='user-auth'),
    path('confirm/', api.ConfirmApi.as_view(), name='user-confirm'),
    path('confirm-oauth/', api.ConfirmBindORUNBindOAuth.as_view(), name='confirm-oauth'),
    path('tokens/', api.TokenCreateApi.as_view(), name='auth-token'),
    path('mfa/verify/', api.MFAChallengeVerifyApi.as_view(), name='mfa-verify'),
    path('mfa/challenge/', api.MFAChallengeVerifyApi.as_view(), name='mfa-challenge'),
    path('mfa/select/', api.MFASendCodeApi.as_view(), name='mfa-select'),
    path('mfa/send-code/', api.MFASendCodeApi.as_view(), name='mfa-send-codej'),
    path('password/verify/', api.UserPasswordVerifyApi.as_view(), name='user-password-verify'),
    path('login-confirm-ticket/status/', api.TicketStatusApi.as_view(), name='login-confirm-ticket-status'),
]

urlpatterns += router.urls
