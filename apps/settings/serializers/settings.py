# coding: utf-8

from .basic import BasicSettingSerializer
from .other import OtherSettingSerializer
from .email import EmailSettingSerializer, EmailContentSettingSerializer
from .auth import (
    LDAPSettingSerializer, OIDCSettingSerializer, KeycloakSettingSerializer,
    CASSettingSerializer, RadiusSettingSerializer,
)
from .terminal import TerminalSettingSerializer
from .security import SecuritySettingSerializer
from .cleaning import CleaningSerializer


__all__ = [
    'SettingsSerializer',
]


class SettingsSerializer(
    BasicSettingSerializer,
    LDAPSettingSerializer,
    TerminalSettingSerializer,
    SecuritySettingSerializer,
    EmailSettingSerializer,
    EmailContentSettingSerializer,
    OtherSettingSerializer,
    OIDCSettingSerializer,
    KeycloakSettingSerializer,
    CASSettingSerializer,
    RadiusSettingSerializer,
    CleaningSerializer,
):
    # encrypt_fields теперь используют write_only для определения
    pass
