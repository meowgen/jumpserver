import time
import warnings

try:
    import pymssql
    from pymssql import OperationalError
except ImportError:
    warnings.warn("Import pymssql error", category=ImportWarning)

from common.utils import get_logger
from .db import DatabaseChangePasswordHandler

logger = get_logger(__file__)


class SQLServerChangePasswordHandler(DatabaseChangePasswordHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = None

    def _step_perform_preflight_check(self):
        logger.info('检测条件: 应用用户 {} 对应用 {} 的可连接性'.format(
            self.task.system_user.username, self.task.app)
        )
        try:
            conn = pymssql.connect(
                server=self.task.app.attrs.get('host'),
                port=self.task.app.attrs.get('port'),
                user=self.task.system_user.username,
                password=self.task.system_user.password,
            )
        except OperationalError as e:
            self.log_error(
                f'\n检测结果: 应用用户 {self.task.system_user.username}\n'
                f' 对应用 {self.task.app} 不可连接'
            )
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
                logger.info('执行改密: 尝试第 ({}/{}) 次'.format(i + 1, self.retry_times))
                try:
                    base_sql = f'alter login {self.task.system_user.username} with password=%s'
                    cur.execute(base_sql, self.task.password)
                    self.conn.commit()
                    self.task.system_user.password = self.task.password
                    self.task.system_user.save()
                except OperationalError as e:
                    logger.info('执行改密结果: 失败')
                    logger.info('原因: {}'.format(e))
                except Exception as e:
                    self.log_error(f'执行结果异常，原因: {e}')
                    break
                else:
                    logger.info('执行改密结果: 成功')
                    break
            self.conn.close()

    def _step_perform_verify_auth(self):
        logger.info("(注意: 本步骤的执行结果为改密任务最终是否成功的标志)")
        for i in range(self.retry_times):
            logger.info('执行改密后对认证信息的校验: 尝试第 ({}/{}) 次'
                        ''.format(i + 1, self.retry_times))
            try:
                conn = pymssql.connect(
                    server=self.task.app.attrs.get('host'),
                    port=self.task.app.attrs.get('port'),
                    user=self.task.system_user.username,
                    password=self.task.password,
                )
            except OperationalError as e:
                logger.info('执行改密后对认证信息的校验结果: 失败')
                self.log_error('原因: {}'.format(e))
                if e.args[0][0] == 18456:
                    raise self.PerformVerifyAuthErrorException(e)
            else:
                logger.info('执行改密后对认证信息的校验结果: 成功')
                conn.close()
                return

            time.sleep(1)
        logger.info('(注意: 可能由于网络不可达或连接超时等原因导致认证信息校验失败)')
        raise self.InterruptException()
