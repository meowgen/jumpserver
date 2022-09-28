# -*- coding: utf-8 -*-
#
from django.conf import settings

from common.utils import get_logger
from common.utils.timezone import local_now_display

from .handlers import AssetChangePasswordHandler
from ..base.manager import BaseExecutionManager
from ...serializers import PlanExecutionTaskBackUpSerializer

logger = get_logger(__name__)


class AssetExecutionManager(BaseExecutionManager):
    def get_handler_cls(self):
        return AssetChangePasswordHandler

    def on_tasks_pre_run(self, tasks):
        logger.info('Совет: об изменении информации аутентификации пользователя {} для связанного ресурса в плане паролей'.format(self.execution.username))
        if settings.CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED:
            logger.info('Совет: режим безопасности плана шифрования включен, и привилегированная учетная запись актива не может быть изменена')
        logger.info('Приступить к реализации плана шифрования ({}) {}'.format(self.execution.plan, local_now_display()))

    def on_per_task_pre_run(self, task, total, index):
        logger.info('\n\033[33m# План расшифровки: {} из {}\033[0m'.format(index, total))

    @property
    def task_back_up_serializer(self):
        return PlanExecutionTaskBackUpSerializer
