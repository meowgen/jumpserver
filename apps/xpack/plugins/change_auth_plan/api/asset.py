# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404
from rest_framework import status, mixins, viewsets
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _

from common.utils import get_object_or_none
from orgs.mixins.api import OrgBulkModelViewSet, OrgGenericViewSet
from orgs.mixins import generics

from .. import serializers
from ..tasks import (
    execute_change_auth_plan, start_change_auth_task
)
from ..models import (
    ChangeAuthPlan, ChangeAuthPlanExecution, ChangeAuthPlanTask,
    ApplicationChangeAuthPlan
)

__all__ = [
    'PlanViewSet', 'PlanExecutionViewSet', 'PlanExecutionSubtaskViewSet',
    'PlanAddAssetApi', 'PlanRemoveAssetApi', 'PlanNodeAddRemoveApi',
    'PlanAssetsApi',
]


class PlanViewSet(OrgBulkModelViewSet):
    model = ChangeAuthPlan
    filter_fields = ('name', 'username', 'password_strategy')
    search_fields = filter_fields
    ordering_fields = ('name',)
    serializer_class = serializers.PlanSerializer


class PlanAssetsApi(generics.ListAPIView):
    serializer_class = serializers.PlanAssetsSerializer
    filter_fields = ("hostname", "ip")
    search_fields = filter_fields

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(ChangeAuthPlan, pk=pk)

    def get_queryset(self):
        plan = self.get_object()
        assets = plan.get_all_assets().only(
            *self.serializer_class.Meta.only_fields
        )
        return assets


class PlanRemoveAssetApi(generics.RetrieveUpdateAPIView):
    model = ChangeAuthPlan
    serializer_class = serializers.PlanUpdateAssetSerializer

    def update(self, request, *args, **kwargs):
        plan = self.get_object()
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response({'error': serializer.errors})

        assets = serializer.validated_data.get('assets')
        if assets:
            plan.assets.remove(*tuple(assets))
        return Response({'msg': 'ok'})


class PlanAddAssetApi(generics.RetrieveUpdateAPIView):
    model = ChangeAuthPlan
    serializer_class = serializers.PlanUpdateAssetSerializer

    def update(self, request, *args, **kwargs):
        plan = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data.get('assets')
            if assets:
                plan.assets.add(*tuple(assets))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class PlanNodeAddRemoveApi(generics.RetrieveUpdateAPIView):
    model = ChangeAuthPlan
    serializer_class = serializers.PlanUpdateNodeSerializer

    def update(self, request, *args, **kwargs):
        action_params = ['add', 'remove']
        action = request.query_params.get('action')
        if action not in action_params:
            err_info = _("The parameter 'action' must be [{}]".format(','.join(action_params)))
            return Response({"error": err_info})

        plan = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            nodes = serializer.validated_data.get('nodes')
            if nodes:
                # eg: plan.nodes.add(*tuple(assets))
                getattr(plan.nodes, action)(*tuple(nodes))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class PlanExecutionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                           mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = serializers.PlanExecutionSerializer
    search_fields =('trigger', )
    filterset_fields = ('trigger', 'plan_id')

    def get_queryset(self):
        queryset = ChangeAuthPlanExecution.objects.all()
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pid = serializer.data.get('plan')
        task = execute_change_auth_plan.delay(
            pid=pid, trigger=ChangeAuthPlanExecution.Trigger.manual
        )
        return Response({'task': task.id}, status=status.HTTP_201_CREATED)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = queryset.order_by('-date_start')
        return queryset


class PlanExecutionSubtaskViewSet(mixins.UpdateModelMixin,
                                  mixins.ListModelMixin,
                                  OrgGenericViewSet):
    serializer_class = serializers.PlanExecutionTaskSerializer
    filter_fields = ['username', 'asset', 'reason']
    search_fields = ['username', 'reason', 'asset__hostname']

    rbac_perms = {
        'PUT': 'xpack.change_changeauthplantask'
    }

    def get_queryset(self):
        return ChangeAuthPlanTask.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        task = start_change_auth_task.delay(tid=instance.id)
        return Response({'task': task.id})

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        eid = self.request.GET.get('plan_execution_id')
        execution = get_object_or_none(ChangeAuthPlanExecution, pk=eid)
        if execution:
            queryset = queryset.filter(execution=execution)
        queryset = queryset.order_by('is_success', '-date_start')
        return queryset
