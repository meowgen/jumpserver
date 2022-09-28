# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from assets.models import Node, SystemUser, Asset, Platform
from assets.serializers import ProtocolsField
from perms.serializers.base import ActionsField

__all__ = [
    'NodeGrantedSerializer',
    'AssetGrantedSerializer',
    'ActionsSerializer', 'AssetSystemUserSerializer',
    'RemoteAppSystemUserSerializer',
    'DatabaseAppSystemUserSerializer',
    'K8sAppSystemUserSerializer',
]


class AssetSystemUserSerializer(serializers.ModelSerializer):
    actions = ActionsField(read_only=True)

    class Meta:
        model = SystemUser
        only_fields = (
            'id', 'name', 'username', 'priority', 'protocol', 'login_mode',
            'sftp_root', 'username_same_with_user', 'su_enabled', 'su_from',
        )
        fields = list(only_fields) + ["actions"]
        read_only_fields = fields


class AssetGrantedSerializer(serializers.ModelSerializer):
    protocols = ProtocolsField(label=_('Protocols'), required=False, read_only=True)
    platform = serializers.SlugRelatedField(
        slug_field='name', queryset=Platform.objects.all(), label=_("Platform")
    )

    class Meta:
        model = Asset
        only_fields = [
            "id", "hostname", "ip", "protocols", "os", 'domain',
            "platform", "comment", "org_id", "is_active"
        ]
        fields = only_fields + ['org_name']
        read_only_fields = fields


class NodeGrantedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = [
            'id', 'name', 'key', 'value', 'org_id', "assets_amount"
        ]
        read_only_fields = fields


class ActionsSerializer(serializers.Serializer):
    actions = ActionsField(read_only=True)


class RemoteAppSystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        only_fields = (
            'id', 'name', 'username', 'priority', 'protocol', 'login_mode',
        )
        fields = list(only_fields)
        read_only_fields = fields


class DatabaseAppSystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        only_fields = (
            'id', 'name', 'username', 'priority', 'protocol', 'login_mode',
        )
        fields = list(only_fields)
        read_only_fields = fields


class K8sAppSystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        only_fields = (
            'id', 'name', 'username', 'priority', 'protocol', 'login_mode',
        )
        fields = list(only_fields)
        read_only_fields = fields

