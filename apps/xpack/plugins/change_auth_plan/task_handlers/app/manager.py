# -*- coding: utf-8 -*-
#
from common.utils import get_logger
from .handlers import handler_mapper
from ..base.manager import BaseExecutionManager
from ...serializers import AppPlanExecutionTaskBackUpSerializer

logger = get_logger(__name__)


class AppExecutionManager(BaseExecutionManager):
    def get_handler_cls(self):
        tp = self.execution.plan.type
        try:
            return handler_mapper[tp]
        except IndexError:
            raise ValueError("Change auth handler not found: {}".format(tp))

    def on_tasks_pre_run(self, tasks):
        apps = [str(task.app) for task in tasks]
        apps_display = ','.join(apps[:3])
        if len(apps) > 3:
            apps_display += ' ...'

        logger.info('\n准备开始执行改密计划 ({})'.format(str(self.execution.plan)))
        logger.info('提示: 即将变更改密计划中 {} {} 的认证信息'.format(
            self.execution.plan.category, apps_display
        ))

    def on_per_task_pre_run(self, task, total, index):
        logger.info('\n\033[33m# 改密计划正在更改: 第 {} 个，共 {} 个\033[0m'.format(index, total))

    @property
    def task_back_up_serializer(self):
        return AppPlanExecutionTaskBackUpSerializer
