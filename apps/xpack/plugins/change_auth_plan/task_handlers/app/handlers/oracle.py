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
        logger.info('Условие обнаружения: подключение системного пользователя {} к приложению {}'.format(
            self.task.system_user.username, self.task.app)
        )
        param_dict = self.make_params()
        try:
            conn = cx_Oracle.connect(**param_dict)
        except DatabaseError as e:
            self.log_error(
                f'\nРезультат теста: системный пользователь {self.task.system_user.username}'
                f' к приложению {self.task.app} не подключаемый'
            )
            self.log_error('Причина: {}'.format(e))
            raise self.PerformPreflightCheckErrorException(e)
        else:
            logger.info('\nРезультат теста: системный пользователь {} к приложению {} подключаемый'.format(
                self.task.system_user.username, self.task.app)
            )
            self.conn = conn

    def _step_perform_change_auth(self):
        if self.conn is None:
            self.log_error('\nПожалуйста, выполните определение условий перед шифрованием')
        else:
            cursor = self.conn.cursor()
            for i in range(self.retry_times):
                logger.info('Выполнить шифрование: ({}/{})'.format(i + 1, self.retry_times))
                try:
                    cursor.execute(
                        f'alter user {self.task.system_user.username} '
                        f'identified by "{self.task.password}"',
                    )
                    self.task.system_user.password = self.task.password
                    self.task.system_user.save()
                except DatabaseError as e:
                    logger.info('Выполнить результат расшифровки: провал')
                    logger.info('Причина: {}'.format(e))
                except Exception as e:
                    self.log_error(f'Результат выполнения ненормальный, причина: {e}')
                    break
                else:
                    logger.info('Выполнить результат расшифровки: успех')
                    cursor.close()
                    self.conn.close()
                    return
            cursor.close()
            self.conn.close()
            raise self.MultipleAttemptAfterErrorException()

    def _step_perform_verify_auth(self):
        logger.info("(Примечание: результат выполнения этого шага является признаком того, успешно ли завершена задача шифрования)")
        for i in range(self.retry_times):
            logger.info('Проверка аутентификационных данных после изменения шифрования: попытка ({}/{}) раз'.format(i + 1, self.retry_times))
            param_dict = self.make_params(has_changed=True)
            try:
                conn = cx_Oracle.connect(**param_dict)
            except DatabaseError as e:
                self.log_error('Результат проверки аутентификационных данных после выполнения шифрования: провал')
                self.log_error('Причина: {}'.format(e))
                if e.args[0].code == 1017:
                    raise self.PerformVerifyAuthErrorException(e)
            else:
                logger.info('Результат проверки аутентификационных данных после выполнения шифрования: успех')
                conn.close()
                return

            time.sleep(1)
        logger.info('(Примечание: Проверка информации для аутентификации может завершиться ошибкой из-за недоступности сети или тайм-аута соединения.)')
        raise self.InterruptException()
