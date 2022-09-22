"""
改密计划：资产改密处理类
"""
import time

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from assets.models import AuthBook
from assets.tasks import (
    run_adhoc, test_asset_connectivity_manual, test_user_connectivity
)
from ops.inventory import JMSInventory
from common.utils import encrypt_password, get_logger

from xpack.plugins.change_auth_plan import const
from ..base import BaseChangePasswordHandler
from ...models import ChangeAuthPlan

logger = get_logger(__file__)


class AssetChangePasswordHandler(BaseChangePasswordHandler):
    def get_lock_key(self):
        key = 'KEY_LOCK_CHANGE_AUTH_PLAN_TASK_RUN_{}_{}' \
              ''.format(self.task.username, self.task.asset.id)
        return key

    def clean_dark_msg(self, dark, task_name):
        try:
            msg = dark[self.task.asset.hostname][task_name]['msg']
        except Exception as e:
            logger.debug(e, exc_info=True)
            logger.info('提取原因出现异常: {}'.format(str(e)))
            msg = 'Unknown ({})'.format(dark)
        return msg

    def _step_perform_preflight_check(self):
        asset = self.task.asset
        logger.info('检测条件: 特权用户 {} 对资产 {} 的可连接性'.format(asset.admin_user, asset))
        succeed, dark = test_asset_connectivity_manual(self.task.asset)

        if succeed:
            logger.info('\n检测结果: 特权用户 {} 对资产 {} 可连接'.format(asset.admin_user, asset))
            return
        else:
            self.log_error('\n检测结果: 特权用户 {} 对资产 {} 不可连接'.format(asset.admin_user, asset))
            msg = self.clean_dark_msg(dark, 'ping')
            logger.error('原因: {}'.format(msg))
            raise self.PerformPreflightCheckErrorException(msg)

    def construct_the_task_of_perform_change_ssh_auth(self, name, strategy):
        if not self.task.asset.is_unixlike():
            logger.info("资产 {} 系统平台 {} 不支持推送ssh密钥的Ansible任务".format(
                str(self.task.asset), self.task.asset.platform
            ))
            return []
        tasks = [
            {
                'name': 'create user If it already exists, no operation will be performed',
                'action': {
                    'module': 'user',
                    'args': 'name={}'.format(self.task.username)
                }
            },
        ]
        module = 'authorized_key'
        args = "user={} key='{}'".format(self.task.username, self.task.public_key)
        if strategy == ChangeAuthPlan.SSHKeyStrategy.add:
            args += ' exclusive=no'
        elif strategy == ChangeAuthPlan.SSHKeyStrategy.set:
            args += ' exclusive=yes'
        elif strategy == ChangeAuthPlan.SSHKeyStrategy.set_jms:
            name_remove = 'Perform remove current user ssh auth'
            message = self.task.public_key.split()[2].strip()
            args_remove = "dest=/home/{}/.ssh/authorized_keys regexp='.*{}$' state=absent".format(
                self.task.username, message
            )
            tasks.append({'name': name_remove, 'action': {'module': 'lineinfile', 'args': args_remove}})
        tasks.append({'name': name, 'action': {'module': module, 'args': args}})
        return tasks

    def construct_the_task_of_perform_change_passwd_auth(self, name):
        if self.task.asset.is_unixlike():
            module = 'user'
            algorithm = 'des' if self.task.asset.platform.name == 'AIX' else 'sha512'
            password = encrypt_password(self.task.password, salt="K3mIlKK", algorithm=algorithm)
        elif self.task.asset.is_windows():
            module = 'win_user'
            password = self.task.password
        else:
            logger.info("资产 {} 系统平台 {} 不支持运行 Ansible 任务".format(
                str(self.task.asset), self.task.asset.platform
            ))
            return []
        tasks = list()
        tasks.append({
            'name': name,
            'action': {
                'module': module,
                'args': 'name={} password={} update_password=always'.format(
                    self.task.username, password
                )
            }
        })
        return tasks

    def _step_perform_change_auth(self):
        logger.info('构造执行改密所需要的 Ansible 任务')
        tasks = list()
        execution = self.task.execution

        task_name = ''
        if execution.is_password:
            task_name = 'Perform change password auth'
            tasks.extend(self.construct_the_task_of_perform_change_passwd_auth(task_name))

        if execution.is_ssh_key:
            task_name = 'Perform change ssh auth'
            task = self.construct_the_task_of_perform_change_ssh_auth(
                task_name, execution.ssh_key_strategy
            )
            tasks.extend(task)

        logger.info('构造执行改密所需要的 Ansible 任务完成')

        inventory = JMSInventory([self.task.asset], run_as_admin=True)
        play_name = "{}: ({})".format(
            const.STEP_DESCRIBE_MAP[const.STEP_PERFORM_CHANGE_AUTH], self.task
        )

        for i in range(self.retry_times):
            logger.info('执行改密: 尝试第 ({}/{}) 次'
                        ''.format(i + 1, self.retry_times))
            raw, summary = run_adhoc(play_name, tasks, inventory)

            dark = summary.get('dark')
            if not dark:
                logger.info('执行改密结果: 成功')
                return

            logger.info('执行改密结果: 失败')
            msg = self.clean_dark_msg(dark, task_name)
            logger.info('原因: {}'.format(msg))
            logger.info('(注意: 结果虽然显示执行改密失败, 但也会存在执行改密成功的情况'
                        ', 因为这一步骤由多个小步骤共同完成的)')
            logger.info('所以改密任务的最终结果请以 <{}> 结果为准'.format(
                const.STEP_DESCRIBE_MAP[const.STEP_PERFORM_VERIFY_AUTH])
            )

            if msg.startswith('Invalid/incorrect password'):
                return

            if (i+1) == self.retry_times:
                # 其他未知原因失败, 以校验密码结果为准
                return

            time.sleep(1)

        raise self.MultipleAttemptAfterErrorException()

    def _step_perform_verify_auth(self):
        task_name = "{}: ({})".format(
            const.STEP_DESCRIBE_MAP[const.STEP_PERFORM_VERIFY_AUTH], self.task
        )
        data = {
            'task_name': task_name, 'asset': self.task.asset,
            'username': self.task.username, 'password': self.task.password,
            'private_key': self.task.private_key_file
        }
        logger.info("(注意: 本步骤的执行结果为改密任务最终是否成功的标志)")
        for i in range(self.retry_times):
            logger.info('执行改密后对认证信息的校验: 尝试第 ({}/{}) 次'
                        ''.format(i + 1, self.retry_times))

            raw, summary = test_user_connectivity(**data)

            dark = summary.get('dark')
            if not dark:
                logger.info('执行改密后对认证信息的校验结果: 成功')
                return

            logger.info('执行改密后对认证信息的校验结果: 失败')
            msg = self.clean_dark_msg(dark, 'ping')
            logger.info('原因: {}'.format(msg))

            if msg.startswith('Invalid/incorrect password'):
                raise self.PerformVerifyAuthErrorException(msg)

            time.sleep(1)

        logger.info('(注意: 可能由于网络不可达或连接超时等原因导致认证信息校验失败)')
        raise self.InterruptException()

    def _step_perform_keep_auth(self):
        data = {
            'name': self.task.username, 'asset': self.task.asset,
            'username': self.task.username, 'password': self.task.password,
            'private_key': self.task.private_key, 'public_key': self.task.public_key
        }

        ids = []
        books = AuthBook.objects.filter(username=self.task.username, asset=self.task.asset, systemuser__isnull=True)
        if books.exists():
            ids.extend(books.values_list('id', flat=True))
            books.update(**data)

            # 为了触发信号
            book = books.first()
            for k, v in data.items():
                setattr(book, k, v)
            book.save()
        else:
            book = AuthBook.objects.create(**data)
            ids.append(book.id)

        logger.info('保存账号完成: ids={}'.format(ids))
        return book
