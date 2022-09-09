# -*- coding: utf-8 -*-
#

import datetime
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .models import SyncInstanceTask, SyncInstanceTaskExecution
from common.utils import get_logger
from orgs.utils import tmp_to_org, tmp_to_root_org
from ops.celery.decorator import register_as_period_task

logger = get_logger(__file__)


@shared_task
def run_sync_instance_task(task_id):
    with tmp_to_root_org():
        task = SyncInstanceTask.objects.filter(pk=task_id).first()

    if not task:
        msg = "No cloud sync instances task found: {}".format(task_id)
        logger.error(msg)
        return

    with tmp_to_org(task.org):
        task.execute()


@register_as_period_task(interval=3600*24)
@shared_task
def clean_sync_instance_task_execution_period():
    now = timezone.now()
    days = settings.CLOUD_SYNC_TASK_EXECUTION_KEEP_DAYS
    if days <= 0:
        return
    expired_day = now - datetime.timedelta(days=days)
    SyncInstanceTaskExecution.objects.filter(date_sync__lt=expired_day).delete()
