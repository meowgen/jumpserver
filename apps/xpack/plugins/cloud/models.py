# -*- coding: utf-8 -*-
#
import json
import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string
from celery import current_task
from common.utils import get_logger, lazyproperty
from common.mixins import CommonModelMixin
from ops.mixin import PeriodTaskModelMixin
from orgs.mixins.models import OrgModelMixin
from .providers.base import BaseProvider
from .const import (
    ProviderChoices, HostnameStrategyChoices, ExecutionStatusChoices,
    InstanceStatusChoices,
)


logger = get_logger(__file__)

__all__ = [
    'Account', 'SyncInstanceTask', 'SyncInstanceTaskExecution', 'SyncInstanceDetail',
]


class Account(CommonModelMixin, OrgModelMixin):
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    provider = models.CharField(
        max_length=128, verbose_name=_('Provider'), default=ProviderChoices.aliyun,
        choices=ProviderChoices.choices,
    )
    attrs = models.JSONField(default=dict, verbose_name=_('Attrs'))
    validity = models.BooleanField(max_length=2, verbose_name=_('Validity'), default=False)
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Cloud account")
        permissions = [
            ('test_account', _('Test cloud account'))
        ]

    def __str__(self):
        return f'{self.name}({self.provider_display})'

    @property
    def provider_display(self):
        return dict(ProviderChoices.choices).get(self.provider)

    @lazyproperty
    def provider_instance(self) -> BaseProvider:
        path = f'xpack.plugins.cloud.providers.{self.provider}.Provider'
        provider_class = import_string(path)
        provider = provider_class(account=self)
        return provider

    @lazyproperty
    def provider_regions(self):
        return self.provider_instance.get_regions()

    def is_valid(self, return_tuples=False):
        return self.provider_instance.is_valid(return_tuples=return_tuples)

    def update_validity(self, validity):
        self.validity = validity
        self.save()

    def check_update_validity(self):
        validity = self.is_valid()
        self.update_validity(validity)
        return validity

    def save(self, **kwargs):
        self.validity = self.is_valid()
        return super().save(**kwargs)


def ip_network_segment_group_default():
    return ['*']


class SyncInstanceTask(PeriodTaskModelMixin, OrgModelMixin):
    account = models.ForeignKey(
        Account, null=True, on_delete=models.SET_NULL, verbose_name=_("Account")
    )
    regions = models.JSONField(
        default=list, verbose_name=_("Regions")
    )
    hostname_strategy = models.CharField(
        max_length=128, blank=True, verbose_name=_('Hostname strategy'),
        default=HostnameStrategyChoices.instance_name_partial_ip,
        choices=HostnameStrategyChoices.choices,
    )
    node = models.ForeignKey(
        'assets.Node', null=True, on_delete=models.SET_NULL, verbose_name=_("Node")
    )
    unix_admin_user = models.ForeignKey(
        'assets.SystemUser', null=True, on_delete=models.SET_NULL,
        related_name='unix_sync_instance_task', verbose_name=_("Unix admin user")
    )
    windows_admin_user = models.ForeignKey(
        'assets.SystemUser', null=True, on_delete=models.SET_NULL,
        related_name='windows_sync_instance_task', verbose_name=_("Windows admin user")
    )
    protocols = models.CharField(
        max_length=128, default='ssh/22 rdp/3389', blank=True, verbose_name=_("Protocols")
    )
    ip_network_segment_group = models.JSONField(
        default=ip_network_segment_group_default, verbose_name=_('IP network segment group')
    )
    is_always_update = models.BooleanField(
        default=False, verbose_name=_('Always update')
    )
    comment = models.TextField(
        max_length=2048, default='', blank=True, verbose_name=_('Comment')
    )
    date_last_sync = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date last sync')
    )
    created_by = models.CharField(
        max_length=32, null=True, blank=True, verbose_name=_('Created by')
    )
    date_created = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, verbose_name=_('Date created')
    )

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Sync instance task")

    def __str__(self):
        return self.name

    def get_register_task(self):
        from .tasks import run_sync_instance_task
        name = "cloud_sync_isntances_period_{}".format(str(self.id)[:8])
        task = run_sync_instance_task.name
        args = (str(self.id),)
        kwargs = {}
        return name, task, args, kwargs

    @property
    def interval_ratio(self):
        return 3600, 'h'

    @property
    def display_regions(self):
        regions = []
        for region_id in self.regions:
            region_name = self.account.provider_regions.get(region_id)
            regions.append(region_name)
        return regions

    def execute(self):
        try:
            hid = current_task.request.id
        except AttributeError:
            logger.debug('No current task id')
            hid = str(uuid.uuid4())
        if not self.account:
            print("Cloud account lost, please check")
            return
        execution = SyncInstanceTaskExecution.objects.create(id=hid, task=self)
        return execution.start()


class SyncInstanceTaskExecution(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task = models.ForeignKey(
        SyncInstanceTask, on_delete=models.CASCADE, verbose_name=_('Sync instance task')
    )
    result = models.JSONField(default=dict, verbose_name=_('Result'))
    status = models.SmallIntegerField(
        verbose_name=_('Status'),
        default=ExecutionStatusChoices.succeed, choices=ExecutionStatusChoices.choices,
    )
    reason = models.CharField(
        max_length=128, default='-', blank=True, verbose_name=_('Reason')
    )
    date_sync = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, verbose_name=_('Date sync')
    )

    class Meta:
        verbose_name = _('Sync instance task execution')

    def start(self):
        from .utils import SyncTaskManager
        manager = SyncTaskManager(execution=self)
        return manager.run()

    def summary(self):
        summary = {k: len(v) for k, v in self.result.items()}
        succeed = summary.pop('succeed', None)
        failed = summary.pop('failed', None)
        exist = summary.pop('exist', None)
        if succeed is not None:
            summary['new'] = succeed
        if failed is not None:
            summary['unsync'] = failed
        if exist is not None:
            summary['sync'] = exist
        return summary


class SyncInstanceDetail(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task = models.ForeignKey(
        SyncInstanceTask, on_delete=models.CASCADE, verbose_name=_('Sync task')
    )
    execution = models.ForeignKey(
        SyncInstanceTaskExecution, on_delete=models.CASCADE,
        verbose_name=_('Sync instance task history')
    )
    instance_id = models.CharField(
        max_length=128, null=False, blank=True, verbose_name=_('Instance')
    )
    region = models.CharField(
        max_length=128, null=False, blank=True, verbose_name=_('Region')
    )
    asset = models.ForeignKey(
        'assets.Asset', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('Asset')
    )
    status = models.SmallIntegerField(
        default=InstanceStatusChoices.sync, choices=InstanceStatusChoices.choices,
        verbose_name=_('Status'),
    )
    date_sync = models.DateTimeField(
        auto_now=True, null=True, blank=True, verbose_name=_('Date sync')
    )

    class Meta:
        verbose_name = _('Sync instance detail')

    @property
    def region_name(self):
        return self.task.account.provider_regions.get(self.region)

    @lazyproperty
    def asset_display(self):
        return str(self.asset)

    @lazyproperty
    def asset_ip(self):
        return self.asset.ip
