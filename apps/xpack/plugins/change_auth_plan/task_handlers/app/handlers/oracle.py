"""
改密计划：各类型数据库改密处理类
"""
import time
import warnings
import os

try:
    import cx_Oracle
    from cx_Oracle import DatabaseError

    lib_dir = '/opt/oracle/instantclient'
    lib_dir = os.environ.get('ORACLE_INSTANT_CLIENT_DIR') or lib_dir
    cx_Oracle.init_oracle_client(lib_dir)
except ImportError:
    warnings.warn("Import cx_Oracle error", category=ImportWarning)

from common.utils import get_logger
from .db import DatabaseChangePasswordHandler

logger = get_logger(__file__)


class OracleChangePasswordHandler(DatabaseChangePasswordHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def make_params(self, has_changed=False):
        host = self.task.app.attrs.get('host')
        port = self.task.app.attrs.get('port')
        service_name = self.task.app.attrs.get('database')
        system_user_passwd = self.task.system_user.password
        task_passwd = self.task.password
        params_dict = {
            'user': self.task.system_user.username,
            'password': task_passwd if has_changed else system_user_passwd,
            'dsn': cx_Oracle.makedsn(host, port, service_name=service_name)
        }
        if self.task.system_user.username == 'sys':
            params_dict.update({'mode': cx_Oracle.SYSDBA})
        return params_dict

    def _step_perform_preflight_check(self):
        logger.info('检测条件: 应用用户 {} 对应用 {} 的可连接性'.format(
            self.task.system_user.username, self.task.app)
        )
        param_dict = self.make_params()
        try:
            conn = cx_Oracle.connect(**param_dict)
        except DatabaseError as e:
            self.log_error(
                f'\n检测结果: 应用用户 {self.task.system_user.username}'
                f' 对应用 {self.task.app} 不可连接'
            )
            self.log_error('原因: {}'.format(e))
            raise self.PerformPreflightCheckErrorException(e)
        else:
            logger.info('\n检测结果: 应用用户 {} 对应用 {} 可连接'.format(
                self.task.system_user.username, self.task.app)
            )
            self.conn = conn

    def _step_perform_change_auth(self):
        if self.conn is None:
            self.log_error('\n请先执行改密前的条件检测')
        else:
            cursor = self.conn.cursor()
            for i in range(self.retry_times):
                logger.info('执行改密: 尝试第 ({}/{}) 次'.format(i + 1, self.retry_times))
                try:
                    cursor.execute(
                        f'alter user {self.task.system_user.username} '
                        f'identified by "{self.task.password}"',
                    )
                    self.task.system_user.password = self.task.password
                    self.task.system_user.save()
                except DatabaseError as e:
                    logger.info('执行改密结果: 失败')
                    logger.info('原因: {}'.format(e))
                except Exception as e:
                    self.log_error(f'执行结果异常，原因: {e}')
                    break
                else:
                    logger.info('执行改密结果: 成功')
                    cursor.close()
                    self.conn.close()
                    return
            cursor.close()
            self.conn.close()
            raise self.MultipleAttemptAfterErrorException()

    def _step_perform_verify_auth(self):
        logger.info("(注意: 本步骤的执行结果为改密任务最终是否成功的标志)")
        for i in range(self.retry_times):
            logger.info('执行改密后对认证信息的校验: 尝试第 ({}/{}) 次'.format(i + 1, self.retry_times))
            param_dict = self.make_params(has_changed=True)
            try:
                conn = cx_Oracle.connect(**param_dict)
            except DatabaseError as e:
                self.log_error('执行改密后对认证信息的校验结果: 失败')
                self.log_error('原因: {}'.format(e))
                if e.args[0].code == 1017:
                    raise self.PerformVerifyAuthErrorException(e)
            else:
                logger.info('执行改密后对认证信息的校验结果: 成功')
                conn.close()
                return

            time.sleep(1)
        logger.info('(注意: 可能由于网络不可达或连接超时等原因导致认证信息校验失败)')
        raise self.InterruptException()
