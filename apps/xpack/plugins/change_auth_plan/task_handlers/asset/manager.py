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
        logger.info('提示: 即将变更改密计划中关联资产上用户 {} 的认证信息'.format(self.execution.username))
        if settings.CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED:
            logger.info('提示: 改密计划安全模式开启中, 不能更改资产的特权账号')
        logger.info('开始执行改密计划 ({}) {}'.format(self.execution.plan, local_now_display()))

    def on_per_task_pre_run(self, task, total, index):
        logger.info('\n\033[33m# 改密计划正在更改: 第 {} 台，共 {} 台\033[0m'.format(index, total))

    @property
    def task_back_up_serializer(self):
        return PlanExecutionTaskBackUpSerializer
