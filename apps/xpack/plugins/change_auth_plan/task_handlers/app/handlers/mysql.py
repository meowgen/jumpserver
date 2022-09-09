"""
改密计划：各类型数据库改密处理类
"""
import time
import warnings

try:
    import pymysql
    from pymysql.err import (
        OperationalError as MySQLOperationalError,
        MySQLError, ProgrammingError
    )
except ImportError:
    warnings.warn("Import pymysql error", category=ImportWarning)

from xpack.plugins.change_auth_plan.errors import DBTestConnectFailedError
from common.utils import get_logger
from .db import DatabaseChangePasswordHandler

logger = get_logger(__file__)


class MySQLChangePasswordHandler(DatabaseChangePasswordHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = None

    def connect_database(self, password):
        host = self.task.app.attrs.get('host')
        port = self.task.app.attrs.get('port')
        user = self.task.system_user.username
        return pymysql.connect(
            host=host, port=port, user=user, password=password,
        )

    def test_connect_database(self, password):
        try:
            conn = self.connect_database(password)
            conn.close()
        except Exception:
            raise DBTestConnectFailedError

    def execute_change_password(self, password):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "alter user %s@%s identified by %s",
                (self.task.system_user.username, '%', password)
            )
        except ProgrammingError:
            cursor.execute(
                "set password for %s@%s=Password(%s)",
                (self.task.system_user.username, '%', password)
            )
        finally:
            cursor.close()

    def _step_perform_preflight_check(self):
        logger.info('检测条件: 应用用户 {} 对应用 {} 的可连接性'.format(
            self.task.system_user.username, self.task.app)
        )
        try:
            password = self.task.system_user.password
            conn = self.connect_database(password)
        except MySQLOperationalError as e:
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
            self.log_error('\n请先执行改密前的条件检测\n')
            return

        for i in range(self.retry_times):
            logger.info('执行改密: 尝试第 ({}/{}) 次'.format(i + 1, self.retry_times))
            try:
                password = self.task.password
                self.execute_change_password(password)
                self.test_connect_database(password)
                self.task.system_user.password = self.task.password
                self.task.system_user.save()
            except MySQLError as e:
                self.log_error('执行改密结果: 失败')
                self.log_error('原因: {}'.format(e))
            except DBTestConnectFailedError as e:
                self.log_error('执行改密成功 但尝试连接测试失败 进行密码回滚')
                self.execute_change_password(self.task.system_user.password)
                self.log_error('原因: {}'.format(e))
            except Exception as e:
                self.log_error(f'执行结果异常，原因: {e}')
                break
            else:
                logger.info('执行改密结果: 成功')
                try:
                    self.conn.close()
                except:
                    pass
                return
        try:
            self.conn.close()
        except:
            pass
        raise self.MultipleAttemptAfterErrorException()

    def _step_perform_verify_auth(self):
        logger.info("(注意: 本步骤的执行结果为改密任务最终是否成功的标志)")
        for i in range(self.retry_times):
            logger.info('执行改密后对认证信息的校验: 尝试第 ({}/{}) 次'
                        ''.format(i + 1, self.retry_times))
            try:
                password = self.task.password
                conn = self.connect_database(password)
            except MySQLOperationalError as e:
                logger.info('执行改密后对认证信息的校验结果: 失败')
                self.log_error('原因: {}'.format(e))
                if e.args[0] == 1045:
                    raise self.PerformVerifyAuthErrorException(e)
            else:
                logger.info('执行改密后对认证信息的校验结果: 成功')
                conn.close()
                return

            time.sleep(1)
        logger.info('(注意: 可能由于网络不可达或连接超时等原因导致认证信息校验失败)')
        raise self.InterruptException()
