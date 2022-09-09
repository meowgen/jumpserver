# -*- coding: utf-8 -*-
#
from django.db import transaction
from rest_framework.response import Response

from orgs.mixins.api import OrgModelViewSet
from common.utils import is_uuid
from . import serializers
from . import models
from .tasks import start_gather_user_execution


class GatherUserTaskViewSet(OrgModelViewSet):
    model = models.GatherUserTask
    serializer_class = serializers.GatherUserTaskSerializer
    filter_fields = ['name']
    search_filters = filter_fields


class GatherUserTaskExecutionViewSet(OrgModelViewSet):
    model = models.GatherUserTaskExecution
    serializer_class = serializers.GatherUserTaskExecutionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        task = self.request.query_params.get('task')
        if not task or not is_uuid(task):
            return self.model.objects.none()
        queryset = queryset.filter(task=task).order_by('-date_start')
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        eid = serializer.data.get('id')
        transaction.on_commit(lambda: start_gather_user_execution.apply_async(
            args=(eid,), task_id=str(eid)
        ))
        return Response({'task': eid}, status=201)
