# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext as _
from rest_framework import serializers

from ..models import (
    ApplicationChangeAuthPlan,
    ApplicationChangeAuthPlanExecution,
    ApplicationChangeAuthPlanTask,
    BaseChangeAuthPlan
)
from .base import BasePlanSerializer, BaseExecutionSerializer

__all__ = [
    'AppPlanSerializer', 'AppPlanExecutionSerializer',
    'AppPlanExecutionTaskSerializer', 'AppPlanExecutionTaskBackUpSerializer'
]


class AppPlanSerializer(BasePlanSerializer):
    class Meta:
        model = ApplicationChangeAuthPlan
        fields = BasePlanSerializer.Meta.fields + [
            'type', 'category', 'apps', 'system_users', 'systemuser_display'
        ]
        read_only_fields = BasePlanSerializer.Meta.read_only_fields
        extra_kwargs = BasePlanSerializer.Meta.extra_kwargs

    def validate(self, attrs):
        password_strategy = attrs.get('password_strategy')
        if password_strategy == BaseChangeAuthPlan.PASSWORD_CUSTOM:
            attrs.pop('password_rules', None)
        else:
            attrs.pop('password', None)
        return attrs


class AppPlanExecutionSerializer(BaseExecutionSerializer):
    class Meta(BaseExecutionSerializer.Meta):
        model = ApplicationChangeAuthPlanExecution

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend([
            'username', 'apps_amount', 'system_users_amount', 'recipients',
            'apps_display', 'system_users_display', 'result_summary'
        ])
        return fields


class AppPlanExecutionTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationChangeAuthPlanTask
        fields = [
            'id', 'app', 'system_user', 'date_start', 'is_success', 'timedelta',
            'reason_display', 'execution', 'system_user_display', 'app_display'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }


class AppPlanExecutionTaskBackUpSerializer(serializers.ModelSerializer):
    app = serializers.SerializerMethodField(label=_('App'))
    system_user = serializers.SerializerMethodField(label=_('System user'))
    reason_display = serializers.ReadOnlyField(label=_('Reason'))
    is_success = serializers.SerializerMethodField(label=_('Is success'))

    class Meta:
        model = ApplicationChangeAuthPlanTask
        fields = [
            'id', 'app', 'system_user', 'type', 'password',
            'reason_display', 'is_success'
        ]

    @staticmethod
    def get_app(obj):
        return str(obj.app)

    @staticmethod
    def get_system_user(obj):
        return str(obj.system_user)

    @staticmethod
    def get_is_success(obj):
        if obj.is_success:
            return _("Success")
        return _("Failed")
