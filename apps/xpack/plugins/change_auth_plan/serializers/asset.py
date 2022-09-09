# -*- coding: utf-8 -*-
#
import socket

from django.utils.translation import ugettext as _
from rest_framework import serializers

from assets.models import Asset, SystemUser
from assets.serializers import AuthSerializerMixin
from common.drf.serializers import SecretReadableMixin
from common.utils import get_logger, ssh_pubkey_gen

from ..models import (
    ChangeAuthPlan,
    ApplicationChangeAuthPlan,
    ChangeAuthPlanExecution,
    ChangeAuthPlanTask,
)
from .base import BasePlanSerializer, BaseExecutionSerializer

logger = get_logger(__file__)

__all__ = [
    'PlanSerializer', 'PlanUpdateAssetSerializer',
    'PlanExecutionSerializer', 'PlanExecutionTaskSerializer',
    'PlanAssetsSerializer', 'PlanUpdateNodeSerializer',
    'PlanSystemUsersUpdateSerializer', 'PlanSystemUsersSerializer',
    'PlanExecutionTaskBackUpSerializer'
]


class PlanSerializer(AuthSerializerMixin, BasePlanSerializer):
    is_password = serializers.BooleanField(default=False, label=_("Change Password"))
    is_ssh_key = serializers.BooleanField(default=False, label=_("Change SSH Key"))
    ssh_key_strategy_display = serializers.ReadOnlyField(
        source='get_ssh_key_strategy_display', label=_('SSH Key strategy'))

    class Meta:
        model = ChangeAuthPlan
        fields = BasePlanSerializer.Meta.fields + [
            'username', 'assets', 'nodes', 'assets_amount', 'nodes_amount', 'is_password',
            'is_ssh_key', 'ssh_key_strategy', 'private_key', 'passphrase', 'ssh_key_strategy_display',
        ]
        read_only_fields = BasePlanSerializer.Meta.read_only_fields + (
            'ssh_key_strategy_display', 'assets_amount', 'nodes_amount',
        )
        extra_kwargs = {**BasePlanSerializer.Meta.extra_kwargs, **{
            'username': {'required': True},
            'private_key': {'write_only': True},
        }}

    @staticmethod
    def validate_username(username):
        # if username.lower() in ['root', 'administrator']:
        #     msg = _("* For security, do not change {}'s password")
        #     raise serializers.ValidationError(msg.format(username))
        return username

    def validate_is_password(self, ok):
        if not ok:
            return ok
        password_strategy = self.initial_data.get('password_strategy')
        password_rules = self.initial_data.get('password_rules')
        password = self.initial_data.get('password')
        msg = None
        if not password_strategy:
            msg = _("This field is required.")
        if password_strategy == ChangeAuthPlan.PASSWORD_CUSTOM:
            if not password and not self.instance:
                msg = _("This field is required.")
        else:
            if not password_rules:
                msg = _("This field is required.")
        if msg:
            raise serializers.ValidationError(msg)
        return ok

    def validate_password_rules(self, password_rules):
        if self.initial_data.get('is_password'):
            super().validate_password_rules(password_rules)
        return password_rules

    def validate(self, attrs):
        is_password = attrs.get('is_password')
        is_ssh_key = attrs.get('is_ssh_key')
        if not is_ssh_key and not is_password:
            raise serializers.ValidationError('Please fill in your password or ssh key')

        if is_password:
            password_strategy = attrs.get('password_strategy')
            if password_strategy == ChangeAuthPlan.PASSWORD_CUSTOM:
                attrs.pop('password_rules', None)
            else:
                attrs.pop('password', None)
        else:
            attrs.pop('password_strategy', None)
            attrs.pop('password_rules', None)
            attrs.pop('password', None)

        private_key = attrs.get('private_key')
        ssh_key_strategy = attrs.get('ssh_key_strategy')

        if is_ssh_key:
            msg = _("This field is required.")
            if not ssh_key_strategy:
                raise serializers.ValidationError({'ssh_key_strategy': msg})
            elif (not private_key and not self.instance) or \
                    (not private_key and self.instance and not self.instance.is_ssh_key):
                raise serializers.ValidationError({'private_key': msg})

        if is_ssh_key and private_key:
            public_key = ssh_pubkey_gen(private_key=private_key, hostname=socket.gethostname())
            attrs["public_key"] = public_key
        else:
            attrs.pop('private_key', None)
            attrs.pop('public_key', None)

        return attrs


class PlanUpdateAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeAuthPlan
        fields = ['id', 'assets']


class PlanUpdateNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeAuthPlan
        fields = ['id', 'nodes']


class PlanAssetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        only_fields = ['id', 'hostname', 'ip']
        fields = tuple(only_fields)


class PlanSystemUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        only_fields = ['id', 'username', 'name']
        fields = tuple(only_fields)


class PlanSystemUsersUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationChangeAuthPlan
        fields = ['id', 'system_users']


class PlanExecutionSerializer(BaseExecutionSerializer):
    class Meta(BaseExecutionSerializer.Meta):
        model = ChangeAuthPlanExecution
        extra_kwargs = {**BaseExecutionSerializer.Meta.extra_kwargs, **{
            'public_key': {'write_only': True},
            'private_key': {'write_only': True},
        }}

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend([
            'username', 'asset_ids', 'node_ids', 'result_summary', 'recipients',
            'password_strategy_display', 'trigger_display', 'assets_amount', 'nodes_amount'
        ])
        return fields


class PlanExecutionTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeAuthPlanTask
        fields = [
            'id', 'username', 'date_start', 'asset', 'is_success', 'timedelta',
            'reason_display', 'execution', 'asset_info'
        ]


class PlanExecutionTaskBackUpSerializer(serializers.ModelSerializer):
    reason_display = serializers.ReadOnlyField(label=_('Reason'))
    asset = serializers.SerializerMethodField(label=_('Asset'))
    is_success = serializers.SerializerMethodField(label=_('Is success'))

    class Meta:
        model = ChangeAuthPlanTask
        fields = [
            'id', 'asset', 'username', 'password', 'public_key', 'private_key',
            'reason_display', 'is_success'
        ]

    @staticmethod
    def get_asset(obj):
        return str(obj.asset)

    @staticmethod
    def get_is_success(obj):
        if obj.is_success:
            return _("Success")
        return _("Failed")
