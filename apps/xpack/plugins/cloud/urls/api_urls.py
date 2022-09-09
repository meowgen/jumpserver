# -*- coding: utf-8 -*-
#
from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from .. import api

router = BulkRouter()
router.register(r'accounts', api.AccountViewSet, 'account')
router.register(r'sync-instance-tasks', api.SyncInstanceTaskViewSet, 'sync-instance-task')

urlpatterns = [
    path('accounts/<uuid:pk>/test-connective/', api.AccountTestConnectiveApi.as_view(), name='account-test-connectivev'),
    path('regions/', api.RegionsListApi.as_view(), name='get-regions'),
    path('sync-instance-tasks/<uuid:pk>/run/', api.SyncInstanceTaskRunApi.as_view(), name='sync-instance-task-run'),
    path('sync-instance-tasks/<uuid:pk>/instances/', api.TaskInstanceListApi.as_view(), name='task-instance-list'),
    path('sync-instance-tasks/<uuid:pk>/history/', api.TaskHistoryListApi.as_view(), name='task-history-list'),
    path('sync-instance-tasks/<uuid:pk>/released-assets/', api.TaskInstancesReleasedDestroyApi.as_view(), name='destroy-task-released-assets'),
]
urlpatterns += router.urls
