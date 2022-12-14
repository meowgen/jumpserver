# -*- coding: utf-8 -*-
import uuid

from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _

from common.utils import lazyproperty
from orgs.mixins.models import OrgModelMixin

__all__ = ['UserGroup']


class UserGroup(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, null=True,
                                        verbose_name=_('Date created'))
    created_by = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

    @lazyproperty
    def users_amount(self):
        return self.users.count()

    class Meta:
        ordering = ['name']
        unique_together = [('org_id', 'name'),]
        verbose_name = _("User group")

    @classmethod
    def initial(cls):
        default_group = cls.objects.filter(name='Default')
        if not default_group:
            group = cls(name='Default', created_by='System', comment='Default user group')
            group.save()
        else:
            group = default_group[0]
        return group
