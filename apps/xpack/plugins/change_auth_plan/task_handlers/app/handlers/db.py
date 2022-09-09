"""
改密计划：各类型数据库改密处理类
"""

from applications.models import Account
from common.utils import get_logger
from ...base import BaseChangePasswordHandler


logger = get_logger(__file__)


class DatabaseChangePasswordHandler(BaseChangePasswordHandler):
    def get_lock_key(self):
        key = 'KEY_LOCK_APP_CHANGE_AUTH_PLAN_TASK_RUN_{}_{}' \
              ''.format(self.task.system_user.username, self.task.app.id)
        return key

    def _step_perform_keep_auth(self):
        defaults = {
            'app': self.task.app,
            'systemuser': self.task.system_user,
            'password': self.task.password
        }
        account, created = Account.objects.get_or_create(
            defaults=defaults, app=self.task.app,
            systemuser=self.task.system_user
        )

        if not created:
            account.password = self.task.password
            account.save()
            logger.info('账号更新完成: id={}'.format(account.id))
        else:
            logger.info('账号保存完成: id={}'.format(account.id))
        return account
