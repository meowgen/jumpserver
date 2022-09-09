# -*- coding: utf-8 -*-
#
from orgs.mixins import generics
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from rest_framework import status, mixins, viewsets
from rest_framework.response import Response

from common.utils import get_object_or_none
from orgs.mixins.api import OrgBulkModelViewSet, OrgGenericViewSet

from .. import serializers
from ..tasks import (
    start_app_change_auth_task,
    execute_app_change_auth_plan
)
from ..models import (
    ApplicationChangeAuthPlan, 
    ApplicationChangeAuthPlanExecution,
    ApplicationChangeAuthPlanTask
)


class AppPlanExecutionSubtaskViewSet(mixins.UpdateModelMixin,
                                     mixins.ListModelMixin,
                                     OrgGenericViewSet):
    serializer_class = serializers.AppPlanExecutionTaskSerializer
    filter_fields = ['system_user', 'reason']
    search_fields = ['reason', 'system_user__username']

    def get_queryset(self):
        return ApplicationChangeAuthPlanTask.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        task = start_app_change_auth_task.delay(tid=instance.id)
        return Response({'task': task.id})

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        eid = self.request.GET.get('plan_execution_id')
        execution = get_object_or_none(ApplicationChangeAuthPlanExecution, pk=eid)
        if execution:
            queryset = queryset.filter(execution=execution)
        queryset = queryset.order_by('is_success', '-date_start')
        return queryset


class AppPlanViewSet(OrgBulkModelViewSet):
    model = ApplicationChangeAuthPlan
    filter_fields = ('name', 'password_strategy')
    search_fields = filter_fields
    ordering_fields = ('name',)
    ordering = ('name', )
    serializer_class = serializers.AppPlanSerializer


class AppPlanExecutionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                              mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = serializers.AppPlanExecutionSerializer
    search_fields = ('trigger', )
    filterset_fields = ('trigger', 'plan_id')

    def get_queryset(self):
        queryset = ApplicationChangeAuthPlanExecution.objects.all()
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pid = serializer.data.get('plan')
        task = execute_app_change_auth_plan.delay(
            pid=pid, trigger=ApplicationChangeAuthPlanExecution.Trigger.manual
        )
        return Response({'task': task.id}, status=status.HTTP_201_CREATED)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = queryset.order_by('-date_start')
        return queryset


class PlanSystemUsersApi(generics.ListAPIView, generics.UpdateAPIView):
    filter_fields = ("username", "name")
    search_fields = filter_fields
    rbac_perms = {
        'PATCH': 'xpack.change_applicationchangeauthplan'
    }

    def get_serializer_class(self):
        if self.request.query_params.get('action'):
            return serializers.PlanSystemUsersUpdateSerializer
        else:
            return serializers.PlanSystemUsersSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(ApplicationChangeAuthPlan, pk=pk)

    def get_queryset(self):
        plan = self.get_object()
        system_users = plan.system_users.only(
            *self.get_serializer_class().Meta.only_fields
        )
        return system_users

    def update(self, request, *args, **kwargs):
        action_params = ['add', 'remove']
        action = request.query_params.get('action')
        if action not in action_params:
            err_info = _("The parameter 'action' must be [{}]".format(','.join(action_params)))
            return Response({"error": err_info})

        plan = self.get_object()
        serializer = self.get_serializer_class()(data=request.data)
        if serializer.is_valid():
            system_user = serializer.validated_data.get('system_users')
            if system_user:
                getattr(plan.system_users, action)(*tuple(system_user))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})

