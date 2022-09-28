# -*- coding: utf-8 -*-
#
import time

from django.utils import timezone

from common.utils import get_logger
from common.utils.timezone import local_now_display

from .handlers import AccountBackupHandler

logger = get_logger(__name__)


class AccountBackupExecutionManager:
    def __init__(self, execution):
        self.execution = execution
        self.date_start = timezone.now()
        self.time_start = time.time()
        self.date_end = None
        self.time_end = None
        self.timedelta = 0

    def do_run(self):
        execution = self.execution
        logger.info('\n\033[33m# План выполнения резервного копирования учётной записи запущен\033[0m')
        handler = AccountBackupHandler(execution)
        handler.run()

    def pre_run(self):
        self.execution.date_start = self.date_start
        self.execution.save()

    def post_run(self):
        self.time_end = time.time()
        self.date_end = timezone.now()

        logger.info('\n\n' + '-' * 80)
        logger.info('Выполнение плана завершено: {}\n'.format(local_now_display()))
        self.timedelta = self.time_end - self.time_start
        logger.info('Заняло времени: {}s'.format(self.timedelta))
        self.execution.timedelta = self.timedelta
        self.execution.save()

    def run(self):
        self.pre_run()
        self.do_run()
        self.post_run()
