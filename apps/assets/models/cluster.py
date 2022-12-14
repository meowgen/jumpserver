#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


__all__ = ['Cluster']
logger = logging.getLogger(__name__)


class Cluster(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=32, verbose_name=_('Name'))
    admin_user = models.ForeignKey('assets.AdminUser', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Admin user"))
    bandwidth = models.CharField(max_length=32, blank=True, verbose_name=_('Bandwidth'))
    contact = models.CharField(max_length=128, blank=True, verbose_name=_('Contact'))
    phone = models.CharField(max_length=32, blank=True, verbose_name=_('Phone'))
    address = models.CharField(max_length=128, blank=True, verbose_name=_("Address"))
    intranet = models.TextField(blank=True, verbose_name=_('Intranet'))
    extranet = models.TextField(blank=True, verbose_name=_('Extranet'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_('Date created'))
    operator = models.CharField(max_length=32, blank=True, verbose_name=_('Operator'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name

    @classmethod
    def initial(cls):
        return cls.objects.get_or_create(name=_('Default'), created_by=_('System'), comment=_('Default Cluster'))[0]

    class Meta:
        ordering = ['name']
        verbose_name = _("Cluster")
