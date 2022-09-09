# -*- coding: utf-8 -*-
#
import time
import os
from openpyxl import Workbook

from django.conf import settings
from django.utils import timezone

from users.models import User
from common.utils import get_logger
from common.utils.timezone import local_now_display
from common.utils.file import encrypt_and_compress_zip_file

from ...notifications import PlanExecutionTaskMsg

logger = get_logger(__file__)


class BaseExecutionManager:
    task_back_up_serializer: None

    def __init__(self, execution):
        self.execution = execution
        self.date_start = timezone.now()
        self.time_start = time.time()
        self.date_end = None
        self.time_end = None
        self.timedelta = 0
        self.total_tasks = []

    def on_tasks_pre_run(self, tasks):
        raise NotImplementedError

    def on_per_task_pre_run(self, task, total, index):
        raise NotImplementedError

    def create_csv_file(self, tasks, file_name):
        raise NotImplementedError

    def get_handler_cls(self):
        raise NotImplemented

    def do_run(self):
        tasks = self.total_tasks = self.execution.create_plan_tasks()
        self.on_tasks_pre_run(tasks)
        total = len(tasks)

        for index, task in enumerate(tasks, start=1):
            self.on_per_task_pre_run(task, total, index)
            task.start(show_step_info=False)
        self.send_change_password_mail(tasks)

    def send_change_password_mail(self, tasks):
        if not tasks:
            return
        recipients = self.execution.plan_snapshot.get('recipients')
        if not recipients:
            return
        recipients = User.objects.filter(id__in=list(recipients))
        plan_name = self.execution.plan.name
        path = os.path.join(os.path.dirname(settings.BASE_DIR), 'tmp')
        filename = os.path.join(path, f'{plan_name}-{local_now_display()}-{time.time()}.xlsx')
        if not self.create_file(tasks, filename):
            return
        for user in recipients:
            if not user.secret_key:
                attachments = []
            else:
                password = user.secret_key.encode('utf8')
                attachment = os.path.join(path, f'{plan_name}-{local_now_display()}-{time.time()}.zip')
                encrypt_and_compress_zip_file(attachment, password, [filename])
                attachments = [attachment]
            PlanExecutionTaskMsg(plan_name, user).publish(attachments)
        os.remove(filename)

    def pre_run(self):
        self.execution.date_start = self.date_start
        self.execution.save()
        self.show_execution_steps()

    def show_execution_steps(self):
        handle_cls = self.get_handler_cls()
        handle_cls.display_all_steps_info()

    def show_summary(self):
        split_line = '#' * 40
        summary = self.execution.result_summary
        logger.info(f'\n{split_line} 改密计划执行结果汇总 {split_line}')
        logger.info(
            '\n成功: {succeed}, 失败: {failed}, 总数: {total}\n'
            ''.format(**summary)
        )

    def post_run(self):
        self.time_end = time.time()
        self.date_end = timezone.now()

        logger.info('\n\n' + '-' * 80)
        logger.info('改密计划执行结束 {}\n'.format(local_now_display()))
        self.timedelta = int(self.time_end - self.time_start)
        logger.info('用时: {}s'.format(self.timedelta))
        self.execution.timedelta = self.timedelta
        self.execution.save()
        self.show_summary()

    def run(self):
        self.pre_run()
        self.do_run()
        self.post_run()

    def create_file(self, tasks, filename):
        rows = []
        tasks = sorted(tasks, key=lambda x: -x.is_success)
        serializer_cls = self.task_back_up_serializer
        for task in tasks:
            serializer = serializer_cls(task)
            data = serializer.data
            header_fields = serializer.fields
            row_dict = {}
            for field, v in header_fields.items():
                header_name = str(v.label)
                row_dict[header_name] = str(data[field])
            rows.append(row_dict)

        if not rows:
            return False

        header = list(rows[0].keys())
        data = [list(row.values()) for row in rows]
        data.insert(0, header)
        wb = Workbook(filename)
        ws = wb.create_sheet('Sheet1')
        for row in data:
            ws.append(row)
        wb.save(filename)
        return True

