# -*- coding: utf-8 -*-
#

from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, is_uuid
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins.generics import ListAPIView, DestroyAPIView
from xpack.permissions import RBACLicensePermission

from . import models, const, serializers
from .tasks import run_sync_instance_task


logger = get_logger(__file__)


class AccountViewSet(OrgBulkModelViewSet):
    model = models.Account
    filter_fields = ('name', 'provider')
    search_fields = ('name',)
    serializer_class = serializers.AccountSerializer
    permission_classes = (RBACLicensePermission,)


class AccountTestConnectiveApi(APIView):
    permission_classes = (RBACLicensePermission,)
    rbac_perms = {
        'GET': 'xpack.view_account'
    }

    def get(self, request, *args, **kwargs):
        account = get_object_or_404(models.Account, pk=kwargs.get('pk'))
        validity, error = account.is_valid(return_tuples=True)
        account.update_validity(validity=validity)
        if validity:
            return Response({'msg': _('Test connection successful')}, status=200)
        else:
            return Response({'msg': _('Test connection failed: {}').format(error)}, status=400)


class SyncInstanceTaskViewSet(OrgBulkModelViewSet):
    model = models.SyncInstanceTask
    filter_fields = ('name',)
    search_fields = ('name', 'account__name')
    serializer_class = serializers.SyncInstanceTaskSerializer
    permission_classes = (RBACLicensePermission,)


class TaskHistoryListApi(ListAPIView):
    model = models.SyncInstanceTaskExecution
    filter_fields = ('status',)
    serializer_class = serializers.TaskHistorySerializer
    permission_classes = (RBACLicensePermission,)

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        queryset = super().get_queryset()
        queryset = queryset.filter(task=pk).order_by('-date_sync')
        return queryset


class TaskInstanceListApi(ListAPIView):
    filter_fields = ['instance_id', 'region', 'asset__hostname', 'status']
    search_fields = filter_fields
    model = models.SyncInstanceDetail
    serializer_class = serializers.TaskInstanceSerializer
    permission_classes = (RBACLicensePermission,)

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        queryset = super().get_queryset()
        queryset = queryset.filter(task=pk).annotate(asset_display=F("asset__hostname"))
        return queryset


class RegionsListApi(APIView):
    permission_classes = (RBACLicensePermission,)
    rbac_perms = {
        'GET': 'xpack.view_account'
    }

    def get(self, request, *args, **kwargs):
        account_id = request.query_params.get('account_id')

        if account_id is None:
            return Response({'regions': []})

        if not is_uuid(account_id):
            return Response({'msg': 'Query params account_id is not uuid'}, status=400)

        account = get_object_or_404(models.Account, pk=account_id)

        try:
            regions = [
                {'id': region_id, 'name': region_name}
                for region_id, region_name in account.provider_regions.items()
            ]
        except Exception as e:
            error = getattr(e, 'msg', str(e))
            return Response({'msg': 'Get regions failed: {}'.format(error)}, status=400)
        else:
            return Response({'regions': regions})


class TaskInstancesReleasedDestroyApi(DestroyAPIView):
    model = models.SyncInstanceTask
    permission_classes = (RBACLicensePermission,)

    def perform_destroy(self, instance):
        from assets.models import Asset
        instances_released = models.SyncInstanceDetail.objects.filter(
            task=instance, status=const.InstanceStatusChoices.released
        )
        released_asset_ids = instances_released.exclude(asset__isnull=True).values_list('asset__id')
        Asset.objects.filter(id__in=released_asset_ids).delete()


class SyncInstanceTaskRunApi(APIView):
    permission_classes = (RBACLicensePermission,)
    rbac_perms = {
        'GET': 'xpack.add_syncinstancetaskexecution'
    }

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        task = run_sync_instance_task.delay(pk)
        return Response({'task': task.id})
