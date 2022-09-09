# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import OrgResourceModelSerializerMixin

from ops.mixin import PeriodTaskSerializerMixin
from .models import GatherUserTask, GatherUserTaskExecution


class GatherUserTaskSerializer(PeriodTaskSerializerMixin, OrgResourceModelSerializerMixin):
    class Meta:
        model = GatherUserTask
        fields = [
            'id', 'name', 'nodes', 'is_periodic', 'interval',
            'crontab', 'comment', 'date_created', 'date_updated',
            'created_by', 'periodic_display', 'executed_times'
        ]
        read_only_fields = ['date_created', 'date_updated', 'created_by']
        extra_kwargs = {
            'periodic_display': {'label': _('Periodic display')},
            'executed_times': {'label': _('Executed times')},
        }


class GatherUserTaskExecutionSerializer(OrgResourceModelSerializerMixin):
    class Meta:
        model = GatherUserTaskExecution
        fields = [
            'id', 'task', 'date_start', 'timedelta', 'success', 'date_created'
        ]
        read_only_fields = [
            'id', 'date_start', 'timedelta', 'success', 'date_created'
        ]
