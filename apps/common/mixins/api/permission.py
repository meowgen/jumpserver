# -*- coding: utf-8 -*-
#
from django.contrib.auth import get_user_model
from rest_framework.request import Request

from common.utils import lazyproperty


__all__ = ['AllowBulkDestroyMixin', 'RoleAdminMixin', 'RoleUserMixin']


class AllowBulkDestroyMixin:
    def allow_bulk_destroy(self, qs, filtered):
        query = str(filtered.query)
        return '`id` IN (' in query or '`id` =' in query


class RoleAdminMixin:
    kwargs: dict
    user_id_url_kwarg = 'pk'

    @lazyproperty
    def user(self):
        user_id = self.kwargs.get(self.user_id_url_kwarg)
        if hasattr(self, 'swagger_fake_view') and not user_id:
            return self.request.user  # NOQA

        user_model = get_user_model()
        return user_model.objects.get(id=user_id)


class RoleUserMixin:
    request: Request

    @lazyproperty
    def user(self):
        return self.request.user