# -*- coding: utf-8 -*-
#

from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from .. import api

router = BulkRouter()
router.register(r'plan', api.PlanViewSet, 'plan')
router.register(r'app-plan', api.AppPlanViewSet, 'app-plan')
router.register(r'plan-execution', api.PlanExecutionViewSet, 'plan-execution')
router.register(r'app-plan-execution', api.AppPlanExecutionViewSet, 'app-plan-execution')
router.register(r'plan-execution-subtask', api.PlanExecutionSubtaskViewSet, 'plan-execution-subtask')
router.register(r'app-plan-execution-subtask', api.AppPlanExecutionSubtaskViewSet, 'app-plan-execution-subtask')

urlpatterns = [
    path('plan/<uuid:pk>/asset/remove/', api.PlanRemoveAssetApi.as_view(), name='plan-remove-asset'),
    path('plan/<uuid:pk>/asset/add/', api.PlanAddAssetApi.as_view(), name='plan-add-asset'),
    path('plan/<uuid:pk>/nodes/', api.PlanNodeAddRemoveApi.as_view(), name='plan-add-or-remove-node'),
    path('plan/<uuid:pk>/assets/', api.PlanAssetsApi.as_view(), name='plan-assets'),
    path('app-plan/<uuid:pk>/systemusers/', api.PlanSystemUsersApi.as_view(), name='plan-systemusers'),

]

urlpatterns += router.urls
