# -*- coding: utf-8 -*-
#

import os
import re

from django.utils.translation import gettext as _
from rest_framework import viewsets
from celery.result import AsyncResult
from rest_framework import generics
from django_celery_beat.models import PeriodicTask

from common.permissions import IsValidUser
from common.api import LogTailApi
from ..models import CeleryTask
from ..serializers import CeleryResultSerializer, CeleryPeriodTaskSerializer
from ..celery.utils import get_celery_task_log_path
from ..ansible.utils import get_ansible_task_log_path
from common.mixins.api import CommonApiMixin


__all__ = [
    'CeleryTaskLogApi', 'CeleryResultApi', 'CeleryPeriodTaskViewSet',
    'AnsibleTaskLogApi',
]


class CeleryTaskLogApi(LogTailApi):
    permission_classes = (IsValidUser,)
    task = None
    task_id = ''
    pattern = re.compile(r'Task .* succeeded in \d+\.\d+s.*')

    def get(self, request, *args, **kwargs):
        self.task_id = str(kwargs.get('pk'))
        self.task = AsyncResult(self.task_id)
        return super().get(request, *args, **kwargs)

    def filter_line(self, line):
        if self.pattern.match(line):
            line = self.pattern.sub(line, '')
        return line

    def get_log_path(self):
        new_path = get_celery_task_log_path(self.task_id)
        if new_path and os.path.isfile(new_path):
            return new_path
        try:
            task = CeleryTask.objects.get(id=self.task_id)
        except CeleryTask.DoesNotExist:
            return None
        return task.full_log_path

    def is_file_finish_write(self):
        return self.task.ready()

    def get_no_file_message(self, request):
        if self.mark == 'undefined':
            return '.'
        else:
            return _('Waiting task start')


class AnsibleTaskLogApi(LogTailApi):
    permission_classes = (IsValidUser,)

    def get_log_path(self):
        new_path = get_ansible_task_log_path(self.kwargs.get('pk'))
        if new_path and os.path.isfile(new_path):
            return new_path

    def get_no_file_message(self, request):
        if self.mark == 'undefined':
            return '.'
        else:
            return _('Waiting task start')


class CeleryResultApi(generics.RetrieveAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = CeleryResultSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        return AsyncResult(pk)


class CeleryPeriodTaskViewSet(CommonApiMixin, viewsets.ModelViewSet):
    queryset = PeriodicTask.objects.all()
    serializer_class = CeleryPeriodTaskSerializer
    http_method_names = ('get', 'head', 'options', 'patch')

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.exclude(description='')
        return queryset
