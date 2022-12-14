# -*- coding: utf-8 -*-
#

from rest_framework.compat import coreapi, coreschema
from rest_framework import filters
from django.db.models import Q

from .models import Label
from assets.utils import is_query_node_all_assets, get_node


class AssetByNodeFilterBackend(filters.BaseFilterBackend):
    fields = ['node', 'all']

    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name=field, location='query', required=False,
                type='string', example='', description='', schema=None,
            )
            for field in self.fields
        ]

    def filter_node_related_all(self, queryset, node):
        return queryset.filter(
            Q(nodes__key__istartswith=f'{node.key}:') |
            Q(nodes__key=node.key)
        ).distinct()

    def filter_node_related_direct(self, queryset, node):
        return queryset.filter(nodes__key=node.key).distinct()

    def filter_queryset(self, request, queryset, view):
        node = get_node(request)
        if node is None:
            return queryset

        query_all = is_query_node_all_assets(request)
        if query_all:
            return self.filter_node_related_all(queryset, node)
        else:
            return self.filter_node_related_direct(queryset, node)


class FilterAssetByNodeFilterBackend(filters.BaseFilterBackend):
    """
    Необходимо использовать с `assets.api.mixin.FilterAssetByNodeMixin`
    """
    fields = ['node', 'all']

    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name=field, location='query', required=False,
                type='string', example='', description='', schema=None,
            )
            for field in self.fields
        ]

    def filter_queryset(self, request, queryset, view):
        node = view.node
        if node is None:
            return queryset
        query_all = view.is_query_node_all_assets
        if query_all:
            return queryset.filter(
                Q(nodes__key__istartswith=f'{node.key}:') |
                Q(nodes__key=node.key)
            ).distinct()
        else:
            return queryset.filter(nodes__key=node.key).distinct()


class LabelFilterBackend(filters.BaseFilterBackend):
    sep = ':'
    query_arg = 'label'

    def get_schema_fields(self, view):
        example = self.sep.join(['os', 'linux'])
        return [
            coreapi.Field(
                name=self.query_arg, location='query', required=False,
                type='string', example=example, description=''
            )
        ]

    def get_query_labels(self, request):
        labels_query = request.query_params.getlist(self.query_arg)
        if not labels_query:
            return None

        q = None
        for kv in labels_query:
            if '#' in kv:
                self.sep = '#'
            if self.sep not in kv:
                continue
            key, value = kv.strip().split(self.sep)[:2]
            if not all([key, value]):
                continue
            if q:
                q |= Q(name=key, value=value)
            else:
                q = Q(name=key, value=value)
        if not q:
            return []
        labels = Label.objects.filter(q, is_active=True)\
            .values_list('id', flat=True)
        return labels

    def filter_queryset(self, request, queryset, view):
        labels = self.get_query_labels(request)
        if labels is None:
            return queryset
        if len(labels) == 0:
            return queryset.none()
        for label in labels:
            queryset = queryset.filter(labels=label)
        return queryset


class AssetRelatedByNodeFilterBackend(AssetByNodeFilterBackend):
    def filter_node_related_all(self, queryset, node):
        return queryset.filter(
            Q(asset__nodes__key__istartswith=f'{node.key}:') |
            Q(asset__nodes__key=node.key)
        ).distinct()

    def filter_node_related_direct(self, queryset, node):
        return queryset.filter(asset__nodes__key=node.key).distinct()


class IpInFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ips = request.query_params.get('ips')
        if not ips:
            return queryset
        ip_list = [i.strip() for i in ips.split(',')]
        queryset = queryset.filter(ip__in=ip_list)
        return queryset

    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='ips', location='query', required=False, type='string',
                schema=coreschema.String(
                    title='ips',
                    description='ip in filter'
                )
            )
        ]
