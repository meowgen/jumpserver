# -*- coding: utf-8 -*-
#

import uuid
import time
from celery import current_task
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from orgs.mixins.models import OrgModelMixin
from common.utils import get_logger, group_obj_by_count
from ops.mixin import PeriodTaskModelMixin


__all__ = ['GatherUserTask', 'GatherUserTaskExecution']

logger = get_logger(__name__)


class GatherUserTask(PeriodTaskModelMixin, OrgModelMixin):
    nodes = models.ManyToManyField(
        'assets.Node', related_name='gather_user_task', blank=True,
        verbose_name=_("Nodes")
    )
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    created_by = models.CharField(
        max_length=128, null=True, verbose_name=_('Created by')
    )

    def __str__(self):
        return self.name + '@' + str(self.created_by)

    class Meta:
        unique_together = [('org_id', 'name')]
        ordering = ['name']
        verbose_name = _('Gather user task')

    @property
    def executed_times(self):
        return self.executions.all().count()

    def get_register_task(self):
        from .tasks import execute_gather_user_task
        name = "gather_user_period_{}".format(str(self.id)[:8])
        task = execute_gather_user_task.name
        args = (str(self.id),)
        kwargs = {}
        return name, task, args, kwargs

    def get_all_assets(self):
        from assets.models import Node
        nodes = self.nodes.all()
        assets = Node.get_nodes_all_assets(*nodes)
        return assets

    def execute(self):
        try:
            hid = current_task.request.id
        except AttributeError:
            hid = str(uuid.uuid4())
        execution = GatherUserTaskExecution(id=hid, task=self)
        execution.save()
        execution.start()


class GatherUserTaskExecution(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task = models.ForeignKey(
        'GatherUserTask', related_name='executions', on_delete=models.CASCADE,
        verbose_name=_('Task')
    )
    date_start = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Date start')
    )
    timedelta = models.FloatField(
        default=0.0, verbose_name=_('Time'), null=True
    )
    success = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('gather user task execution')

    def start(self):
        from assets.tasks import gather_asset_users
        assets = self.task.get_all_assets()
        if not assets:
            print(_("Assets is empty, please change nodes"))
            return
        time_start = time.time()
        self.date_start = timezone.now()
        self.save()
        try:
            assets_grouped = group_obj_by_count(assets, 50)
            for assets_50 in assets_grouped:
                gather_asset_users(assets_50)
        except Exception as e:
            logger.error(e, exc_info=True)
        finally:
            timedelta = time.time() - time_start
            self.__class__.objects.filter(id=self.id).update(
                timedelta=timedelta, success=True
            )

