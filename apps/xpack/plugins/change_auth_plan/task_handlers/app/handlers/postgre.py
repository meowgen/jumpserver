"""
改密计划：各类型数据库改密处理类
"""
import time
import warnings

from xpack.plugins.change_auth_plan.utils import wrapper_error

try:
    import psycopg2
    from psycopg2 import OperationalError as PostgreOperationalError
except ImportError:
    warnings.warn("Import psycopg2 error", category=ImportWarning)

from common.utils import get_logger
from .db import DatabaseChangePasswordHandler


logger = get_logger(__file__)


class PostgreChangePasswordHandler(DatabaseChangePasswordHandler):
    def _step_perform_preflight_check(self):
        logger.info(
            f'检测条件: 应用用户 {self.task.system_user.username} '
            f'对应用 {self.task.app} 的可连接性'
        )
        try:
            conn = psycopg2.connect(
                user=self.task.system_user.username,
                password=self.task.system_user.password,
                host=self.task.app.attrs.get('host'),
                port=self.task.app.attrs.get('port'),
                database=self.task.app.attrs.get('database')
            )
        except PostgreOperationalError as e:
            logger.error(wrapper_error(
                f'\n检测结果: 应用用户 {self.task.system_user.username}'
                f' 对应用 {self.task.app} 不可连接'
            ))
            logger.error('原因: {}'.format(e))
            raise self.PerformPreflightCheckErrorException(e)
        else:
            logger.info(
                f'\n检测结果: 应用用户 {self.task.system_user.username}'
                f' 对应用 {self.task.app} 可连接'
            )
            self.conn = conn

    def _step_perform_change_auth(self):
        if self.conn is None:
            self.log_error('\n请先执行改密前的条件检测')
        else:
            cur = self.conn.cursor()
            for i in range(self.retry_times):
                logger.info('执行改密: 尝试第 ({}/{}) 次'
                            ''.format(i + 1, self.retry_times))
                try:
                    cur.execute(
                        f"alter user {self.task.system_user.username} "
                        f"with password '{self.task.password}';",
                    )
                    self.conn.commit()
                    self.task.system_user.password = self.task.password
                    self.task.system_user.save()
                except PostgreOperationalError as e:
                    logger.info('执行改密结果: 失败')
                    logger.info('原因: {}'.format(e))
                except Exception as e:
                    self.log_error(f'执行结果异常，原因: {e}')
                    break
                else:
                    logger.info('执行改密结果: 成功')
                    cur.close()
                    self.conn.close()
                    return
            cur.close()
            self.conn.close()
            raise self.MultipleAttemptAfterErrorException()

    def _step_perform_verify_auth(self):
        logger.info("(注意: 本步骤的执行结果为改密任务最终是否成功的标志)")
        for i in range(self.retry_times):
            logger.info('执行改密后对认证信息的校验: 尝试第 ({}/{}) 次'
                        ''.format(i + 1, self.retry_times))
            try:
                conn = psycopg2.connect(
                    user=self.task.system_user.username,
                    password=self.task.password,
                    host=self.task.app.attrs.get('host'),
                    port=self.task.app.attrs.get('port'),
                    database=self.task.app.attrs.get('database')
                )
            except PostgreOperationalError as e:
                logger.info('执行改密后对认证信息的校验结果: 失败')
                logger.error('原因: {}'.format(e))
                if 'password authentication' in e.args[0]:
                    raise self.PerformVerifyAuthErrorException(e)
            else:
                logger.info('执行改密后对认证信息的校验结果: 成功')
                conn.close()
                return

            time.sleep(1)
        logger.info('(注意: 可能由于网络不可达或连接超时等原因导致认证信息校验失败)')
        raise self.InterruptException()
