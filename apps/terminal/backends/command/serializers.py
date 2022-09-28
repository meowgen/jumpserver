# ~*~ coding: utf-8 ~*~
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.utils import pretty_string
from .models import AbstractSessionCommand

__all__ = ['SessionCommandSerializer', 'InsecureCommandAlertSerializer']


class SimpleSessionCommandSerializer(serializers.Serializer):
    user = serializers.CharField(label=_("User"))
    asset = serializers.CharField(max_length=128, label=_("Asset"))
    input = serializers.CharField(max_length=2048, label=_("Command"))
    session = serializers.CharField(max_length=36, label=_("Session ID"))
    risk_level = serializers.ChoiceField(
        required=False, label=_("Risk level"), choices=AbstractSessionCommand.RISK_LEVEL_CHOICES
    )
    org_id = serializers.CharField(max_length=36, required=False, default='', allow_null=True, allow_blank=True)

    def validate_user(self, value):
        if len(value) > 64:
            value = value[:32] + value[-32:]
        return value


class InsecureCommandAlertSerializer(SimpleSessionCommandSerializer):
    pass


class SessionCommandSerializer(SimpleSessionCommandSerializer):
    id = serializers.UUIDField(read_only=True)
    system_user = serializers.CharField(label=_("System user"))
    output = serializers.CharField(max_length=2048, allow_blank=True, label=_("Output"))
    risk_level_display = serializers.SerializerMethodField(label=_('Risk level display'))
    timestamp = serializers.IntegerField(label=_('Timestamp'))
    timestamp_display = serializers.DateTimeField(read_only=True, label=_('Datetime'))
    remote_addr = serializers.CharField(read_only=True, label=_('Remote Address'))

    @staticmethod
    def get_risk_level_display(obj):
        risk_mapper = dict(AbstractSessionCommand.RISK_LEVEL_CHOICES)
        return risk_mapper.get(obj.risk_level)

    def validate_system_user(self, value):
        if len(value) > 64:
            value = pretty_string(value, 64)
        return value
