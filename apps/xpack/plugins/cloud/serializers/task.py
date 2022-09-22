# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.utils.ip import is_ip_network, is_ip_segment
from ops.mixin import PeriodTaskSerializerMixin
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import (
    SyncInstanceTask, SyncInstanceDetail, SyncInstanceTaskExecution,
)
from assets.serializers.asset import ProtocolsField


__all__ = ['SyncInstanceTaskSerializer', 'TaskInstanceSerializer', 'TaskHistorySerializer']


def ip_network_segment_validator(ip_group_child):
    is_valid = ip_group_child == '*' \
               or is_ip_network(ip_group_child) \
               or is_ip_segment(ip_group_child)
    if not is_valid:
        error = _('IP address invalid: `{}`').format(ip_group_child)
        raise serializers.ValidationError(error)


class SyncInstanceTaskSerializer(PeriodTaskSerializerMixin, BulkOrgResourceModelSerializer):
    ip_network_segment_group_help_text = _(
        'Only instances matching the IP range will be synced. <br>'
        'If the instance contains multiple IP addresses, '
        'the first IP address that matches will be used as the IP for the created asset. <br>'
        'The default value of * means sync all instances and randomly match IP addresses. <br>'
        'Format for comma-delimited string, '
        'Such as: 192.168.1.0/24, 10.1.1.1-10.1.1.20'
    )
    history_count = serializers.SerializerMethodField(label=_('History count'))
    instance_count = serializers.SerializerMethodField(label=_('Instance count'))
    regions = serializers.ListField(label=_('Regions'))
    account_display = serializers.ReadOnlyField(source='account.name')
    node_display = serializers.ReadOnlyField(source='node.name')
    unix_admin_user_display = serializers.ReadOnlyField(source='unix_admin_user.name')
    windows_admin_user_display = serializers.ReadOnlyField(source='windows_admin_user.name')
    protocols = ProtocolsField(label=_('Protocols'), required=False, default=['ssh/22', 'rdp/3389'])
    ip_network_segment_group = serializers.ListField(
        child=serializers.CharField(max_length=1024, validators=[ip_network_segment_validator]),
        default=['*'], label=_('IP network segment group'),
        help_text=ip_network_segment_group_help_text,
    )

    class Meta:
        model = SyncInstanceTask
        fields = [
            'id', 'name', 'regions', 'account', 'account_display', 'regions', 'hostname_strategy',
            'node', 'node_display', 'unix_admin_user', 'unix_admin_user_display',
            'windows_admin_user', 'windows_admin_user_display',
            'protocols', 'ip_network_segment_group', 'is_always_update',
            'is_periodic', 'interval', 'crontab', 'comment', 'date_last_sync', 'created_by',
            'date_created', 'history_count', 'instance_count', 'periodic_display'
        ]
        read_only_fields = [
            'account_display', 'unix_admin_user_display', 'windows_admin_user_display',
            'node_display', 'history_count', 'instance_count', 'periodic_display',
            'date_last_sync', 'created_by', 'date_created'
        ]
        extra_kwargs = {
            'unix_admin_user': {'label': _('Linux admin user')},
            'account_display': {'label': _('Account')},
            'unix_admin_user_display': {'label': _('Unix admin user')},
            'windows_admin_user_display': {'label': _('Windows admin user')},
            'node_display': {'label': _('Node')},
            'periodic_display': {'label': _('Periodic display')},
            'is_always_update': {'label': _('Always update')}
        }

    @staticmethod
    def get_history_count(instance):
        return SyncInstanceTaskExecution.objects.filter(task=instance).count()

    @staticmethod
    def get_instance_count(instance):
        return SyncInstanceDetail.objects.filter(task=instance).count()

    @staticmethod
    def validate_protocols(protocols):
        return ' '.join(protocols)


class TaskInstanceSerializer(serializers.ModelSerializer):
    status_display = serializers.ReadOnlyField(source='get_status_display')

    class Meta:
        model = SyncInstanceDetail
        fields = [
            'id', 'task', 'execution', 'instance_id', 'region', 'asset', 'asset_display', 'status',
            'status_display', 'date_sync', 'asset_ip'
        ]


class TaskHistorySerializer(serializers.ModelSerializer):
    status_display = serializers.ReadOnlyField(source='get_status_display')

    class Meta:
        model = SyncInstanceTaskExecution
        fields = [
            'id', 'task', 'summary', 'status', 'status_display', 'reason', 'date_sync'
        ]
