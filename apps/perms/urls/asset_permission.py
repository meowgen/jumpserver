# coding:utf-8

from django.urls import path, include
from rest_framework_bulk.routes import BulkRouter

from .. import api

router = BulkRouter()
router.register('asset-permissions', api.AssetPermissionViewSet, 'asset-permission')
router.register('asset-permissions-users-relations', api.AssetPermissionUserRelationViewSet, 'asset-permissions-users-relation')
router.register('asset-permissions-user-groups-relations', api.AssetPermissionUserGroupRelationViewSet, 'asset-permissions-user-groups-relation')
router.register('asset-permissions-assets-relations', api.AssetPermissionAssetRelationViewSet, 'asset-permissions-assets-relation')
router.register('asset-permissions-nodes-relations', api.AssetPermissionNodeRelationViewSet, 'asset-permissions-nodes-relation')
router.register('asset-permissions-system-users-relations', api.AssetPermissionSystemUserRelationViewSet, 'asset-permissions-system-users-relation')

user_permission_urlpatterns = [
    path('<uuid:pk>/assets/', api.UserAllGrantedAssetsApi.as_view(), name='user-assets'),
    path('assets/', api.MyAllGrantedAssetsApi.as_view(), name='my-assets'),

    path('<uuid:pk>/assets/tree/', api.UserDirectGrantedAssetsAsTreeForAdminApi.as_view(), name='user-assets-as-tree'),
    path('assets/tree/', api.MyAllAssetsAsTreeApi.as_view(), name='my-assets-as-tree'),
    path('ungroup/assets/tree/', api.MyUngroupAssetsAsTreeApi.as_view(), name='my-ungroup-assets-as-tree'),

    path('<uuid:pk>/nodes/', api.UserGrantedNodesForAdminApi.as_view(), name='user-nodes'),
    path('nodes/', api.MyGrantedNodesApi.as_view(), name='my-nodes'),

    path('<uuid:pk>/nodes/tree/', api.MyGrantedNodesAsTreeApi.as_view(), name='user-nodes-as-tree'),
    path('nodes/tree/', api.MyGrantedNodesAsTreeApi.as_view(), name='my-nodes-as-tree'),

    path('<uuid:pk>/nodes/children/', api.UserGrantedNodeChildrenForAdminApi.as_view(), name='user-nodes-children'),
    path('nodes/children/', api.MyGrantedNodeChildrenApi.as_view(), name='my-nodes-children'),

    path('<uuid:pk>/nodes/children/tree/', api.UserGrantedNodeChildrenAsTreeForAdminApi.as_view(), name='user-nodes-children-as-tree'),
    path('nodes/children/tree/', api.MyGrantedNodeChildrenAsTreeApi.as_view(), name='my-nodes-children-as-tree'),

    path('nodes-with-assets/tree/', api.MyGrantedNodesWithAssetsAsTreeApi.as_view(), name='my-nodes-with-assets-as-tree'),

    path('<uuid:pk>/nodes/children-with-assets/tree/', api.UserGrantedNodeChildrenWithAssetsAsTreeApi.as_view(), name='user-nodes-children-with-assets-as-tree'),
    path('nodes/children-with-assets/tree/', api.MyGrantedNodeChildrenWithAssetsAsTreeApi.as_view(), name='my-nodes-children-with-assets-as-tree'),

    path('<uuid:pk>/nodes/<uuid:node_id>/assets/', api.UserGrantedNodeAssetsForAdminApi.as_view(), name='user-node-assets'),
    path('nodes/<uuid:node_id>/assets/', api.MyGrantedNodeAssetsApi.as_view(), name='my-node-assets'),

    path('<uuid:pk>/nodes/ungrouped/assets/', api.UserDirectGrantedAssetsForAdminApi.as_view(), name='user-ungrouped-assets'),
    path('nodes/ungrouped/assets/', api.MyDirectGrantedAssetsApi.as_view(), name='my-ungrouped-assets'),

    path('<uuid:pk>/nodes/favorite/assets/', api.UserFavoriteGrantedAssetsForAdminApi.as_view(), name='user-ungrouped-assets'),
    path('nodes/favorite/assets/', api.MyFavoriteGrantedAssetsApi.as_view(), name='my-ungrouped-assets'),

    # Asset System users
    path('<uuid:pk>/assets/<uuid:asset_id>/system-users/', api.UserGrantedAssetSystemUsersForAdminApi.as_view(), name='user-asset-system-users'),
    path('assets/<uuid:asset_id>/system-users/', api.MyGrantedAssetSystemUsersApi.as_view(), name='my-asset-system-users'),

    path('<uuid:pk>/asset-permissions/cache/', api.UserAssetPermissionsCacheApi.as_view(),
         name='user-asset-permission-cache'),
    path('asset-permissions/cache/', api.UserAssetPermissionsCacheApi.as_view(), name='my-asset-permission-cache'),
]

user_group_permission_urlpatterns = [
    path('<uuid:pk>/assets/', api.UserGroupGrantedAssetsApi.as_view(), name='user-group-assets'),
    path('<uuid:pk>/nodes/', api.UserGroupGrantedNodesApi.as_view(), name='user-group-nodes'),
    path('<uuid:pk>/nodes/children/', api.UserGroupGrantedNodesApi.as_view(), name='user-group-nodes-children'),
    path('<uuid:pk>/nodes/children/tree/', api.UserGroupGrantedNodeChildrenAsTreeApi.as_view(), name='user-group-nodes-children-as-tree'),
    path('<uuid:pk>/nodes/<uuid:node_id>/assets/', api.UserGroupGrantedNodeAssetsApi.as_view(), name='user-group-node-assets'),
    path('<uuid:pk>/assets/<uuid:asset_id>/system-users/', api.UserGroupGrantedAssetSystemUsersApi.as_view(), name='user-group-asset-system-users'),
]

permission_urlpatterns = [
    path('<uuid:pk>/assets/all/', api.AssetPermissionAllAssetListApi.as_view(), name='asset-permission-all-assets'),
    path('<uuid:pk>/users/all/', api.AssetPermissionAllUserListApi.as_view(), name='asset-permission-all-users'),

    path('user/validate/', api.ValidateUserAssetPermissionApi.as_view(), name='validate-user-asset-permission'),
    path('user/actions/', api.GetUserAssetPermissionActionsApi.as_view(), name='get-user-asset-permission-actions'),

]

asset_permission_urlpatterns = [
    # Assets
    path('users/', include(user_permission_urlpatterns)),
    path('user-groups/', include(user_group_permission_urlpatterns)),
    path('asset-permissions/', include(permission_urlpatterns)),
]

asset_permission_urlpatterns += router.urls
