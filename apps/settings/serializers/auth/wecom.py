from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.drf.fields import EncryptedField

__all__ = ['WeComSettingSerializer']


class WeComSettingSerializer(serializers.Serializer):
    WECOM_CORPID = serializers.CharField(max_length=256, required=True, label='corpid')
    WECOM_AGENTID = serializers.CharField(max_length=256, required=True, label='agentid')
    WECOM_SECRET = EncryptedField(max_length=256, required=False, label='secret')
    AUTH_WECOM = serializers.BooleanField(default=False, label=_('Enable WeCom Auth'))
