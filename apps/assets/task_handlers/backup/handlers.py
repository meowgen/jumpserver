import os
import time
from openpyxl import Workbook
from collections import defaultdict, OrderedDict

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models import AuthBook
from assets.serializers import AccountSecretSerializer
from assets.notifications import AccountBackupExecutionTaskMsg
from applications.models import Account
from applications.const import AppType
from applications.serializers import AppAccountSecretSerializer
from users.models import User
from common.utils import get_logger
from common.utils.timezone import local_now_display
from common.utils.file import encrypt_and_compress_zip_file

logger = get_logger(__file__)

PATH = os.path.join(os.path.dirname(settings.BASE_DIR), 'tmp')


class BaseAccountHandler:
    @classmethod
    def unpack_data(cls, serializer_data, data=None):
        if data is None:
            data = {}
        for k, v in serializer_data.items():
            if isinstance(v, OrderedDict):
                cls.unpack_data(v, data)
            else:
                data[k] = v
        return data

    @classmethod
    def get_header_fields(cls, serializer: serializers.Serializer):
        try:
            backup_fields = getattr(serializer, 'Meta').fields_backup
        except AttributeError:
            backup_fields = serializer.fields.keys()
        header_fields = {}
        for field in backup_fields:
            v = serializer.fields[field]
            if isinstance(v, serializers.Serializer):
                _fields = cls.get_header_fields(v)
                header_fields.update(_fields)
            else:
                header_fields[field] = str(v.label)
        return header_fields

    @classmethod
    def create_row(cls, account, serializer_cls, header_fields=None):
        serializer = serializer_cls(account)
        if not header_fields:
            header_fields = cls.get_header_fields(serializer)
        data = cls.unpack_data(serializer.data)
        row_dict = {}
        for field, header_name in header_fields.items():
            row_dict[header_name] = str(data[field])
        return row_dict


class AssetAccountHandler(BaseAccountHandler):
    @staticmethod
    def get_filename(plan_name):
        filename = os.path.join(
            PATH, f'{plan_name}-{_("Asset")}-{local_now_display()}-{time.time()}.xlsx'
        )
        return filename

    @classmethod
    def create_data_map(cls):
        data_map = defaultdict(list)
        sheet_name = AuthBook._meta.verbose_name

        accounts = AuthBook.get_queryset().select_related('systemuser')
        if not accounts.first():
            return data_map

        header_fields = cls.get_header_fields(AccountSecretSerializer(accounts.first()))
        for account in accounts:
            account.load_auth()
            row = cls.create_row(account, AccountSecretSerializer, header_fields)
            if sheet_name not in data_map:
                data_map[sheet_name].append(list(row.keys()))
            data_map[sheet_name].append(list(row.values()))

        logger.info('\n\033[33m- Всего было собрано {} учётных записей ресурсов\033[0m'.format(accounts.count()))
        return data_map


class AppAccountHandler(BaseAccountHandler):
    @staticmethod
    def get_filename(plan_name):
        filename = os.path.join(
            PATH, f'{plan_name}-{_("Application")}-{local_now_display()}-{time.time()}.xlsx'
        )
        return filename

    @classmethod
    def create_data_map(cls):
        data_map = defaultdict(list)
        accounts = Account.get_queryset().select_related('systemuser')
        for account in accounts:
            account.load_auth()
            app_type = account.type
            sheet_name = AppType.get_label(app_type)
            row = cls.create_row(account, AppAccountSecretSerializer)
            if sheet_name not in data_map:
                data_map[sheet_name].append(list(row.keys()))
            data_map[sheet_name].append(list(row.values()))
        logger.info('\n\033[33m- Всего собано {} учётных записей приложений\033[0m'.format(accounts.count()))
        return data_map


handler_map = {
    'asset': AssetAccountHandler,
    'application': AppAccountHandler
}


class AccountBackupHandler:
    def __init__(self, execution):
        self.execution = execution
        self.plan_name = self.execution.plan.name
        self.is_frozen = False

    def create_excel(self):
        logger.info(
            '\n'
            '\033[32m>>> Создаются файлы информации о резервных копиях, связанные с ресурсами или приложениями.\033[0m'
            ''
        )
        # Print task start date
        time_start = time.time()
        files = []
        for account_type in self.execution.types:
            handler = handler_map.get(account_type)
            if not handler:
                continue

            data_map = handler.create_data_map()
            if not data_map:
                continue

            filename = handler.get_filename(self.plan_name)

            wb = Workbook(filename)
            for sheet, data in data_map.items():
                ws = wb.create_sheet(str(sheet))
                for row in data:
                    ws.append(row)
            wb.save(filename)
            files.append(filename)
        timedelta = round((time.time() - time_start), 2)
        logger.info('Действие завершено. Это заняло {} сек.'.format(timedelta))
        return files

    def send_backup_mail(self, files, recipients):
        if not files:
            return
        recipients = User.objects.filter(id__in=list(recipients))
        logger.info(
            '\n'
            '\033[32m>>> Отправить электронное письмо для получения резервной копии\033[0m'
            ''
        )
        plan_name = self.plan_name
        for user in recipients:
            if not user.secret_key:
                attachment_list = []
            else:
                password = user.secret_key.encode('utf8')
                attachment = os.path.join(PATH, f'{plan_name}-{local_now_display()}-{time.time()}.zip')
                encrypt_and_compress_zip_file(attachment, password, files)
                attachment_list = [attachment, ]
            AccountBackupExecutionTaskMsg(plan_name, user).publish(attachment_list)
            logger.info('Электронное письмо было направлено пользователю {} на ({})'.format(user, user.email))
        for file in files:
            os.remove(file)

    def step_perform_task_update(self, is_success, reason):
        self.execution.reason = reason[:1024]
        self.execution.is_success = is_success
        self.execution.save()
        logger.info('Завершено обновление статуса задачи')

    def step_finished(self, is_success):
        if is_success:
            logger.info('Задача выполнена успешно')
        else:
            logger.error('Не удалось выполнить задачу')

    def _run(self):
        is_success = False
        error = '-'
        try:
            recipients = self.execution.plan_snapshot.get('recipients')
            if not recipients:
                logger.info(
                    '\n'
                    '\033[32m>>> Для этой задачи резервного копирования не назначены получатели\033[0m'
                    ''
                )
            else:
                files = self.create_excel()
                self.send_backup_mail(files, recipients)
        except Exception as e:
            self.is_frozen = True
            logger.error('Выполнение задачи было прервано аварийно')
            logger.info('Traceback info: ')
            logger.error(e, exc_info=True)
            error = str(e)
        else:
            is_success = True
        finally:
            reason = error
            self.step_perform_task_update(is_success, reason)
            self.step_finished(is_success)

    def run(self):
        logger.info('Выполнение задачи начинается: {}'.format(local_now_display()))
        time_start = time.time()
        try:
            self._run()
        except Exception as e:
            logger.error('Выполнение задачи было прервано аварийно')
            logger.error('Traceback info: ')
            logger.error(e, exc_info=True)
        finally:
            logger.info('\Завершение выполнения задачи: {}'.format(local_now_display()))
            timedelta = round((time.time() - time_start), 2)
            logger.info('Затраченное время: {}'.format(timedelta))
