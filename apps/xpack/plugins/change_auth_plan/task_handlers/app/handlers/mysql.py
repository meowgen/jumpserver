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
        logger.info('Условие обнаружения: подключение пользователя приложения {} к приложению {}'.format(
            self.task.system_user.username, self.task.app)
        )
        try:
            password = self.task.system_user.password
            conn = self.connect_database(password)
        except MySQLOperationalError as e:
            self.log_error(
                f'\nРезультат теста: Системный пользователь {self.task.system_user.username}\n'
                f' к приложению {self.task.app} не подключаемый'
            )
            logger.error('Причина: {}'.format(e))
            raise self.PerformPreflightCheckErrorException(e)
        else:
            logger.info(
                f'\nРезультат теста: Системный пользователь {self.task.system_user.username}'
                f' к приложению {self.task.app} подключаемый'
            )
            self.conn = conn

    def _step_perform_change_auth(self):
        if self.conn is None:
            self.log_error('\nПожалуйста, выполните определение условий перед шифрованием\n')
            return

        for i in range(self.retry_times):
            logger.info('Выполнить шифрование: ({}/{})'.format(i + 1, self.retry_times))
            try:
                password = self.task.password
                self.execute_change_password(password)
                self.test_connect_database(password)
                self.task.system_user.password = self.task.password
                self.task.system_user.save()
            except MySQLError as e:
                self.log_error('Выполнить результат расшифровки: провал')
                self.log_error('Причина: {}'.format(e))
            except DBTestConnectFailedError as e:
                self.log_error('Смена пароля прошла успешно, но проверка соединения не удалась, и пароль откатился')
                self.execute_change_password(self.task.system_user.password)
                self.log_error('Причина: {}'.format(e))
            except Exception as e:
                self.log_error(f'Результат выполнения ненормальный, причина: {e}')
                break
            else:
                logger.info('Выполнить результат расшифровки: успех')
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
        logger.info("(Уведомление: Результат выполнения этого шага является признаком того, успешно ли завершена задача шифрования.)")
        for i in range(self.retry_times):
            logger.info('Проверка аутентификационных данных после выполнения шифрования: ({}/{})'
                        ''.format(i + 1, self.retry_times))
            try:
                password = self.task.password
                conn = self.connect_database(password)
            except MySQLOperationalError as e:
                logger.info('Результат проверки аутентификационных данных после выполнения шифрования: провал')
                self.log_error('Причина: {}'.format(e))
                if e.args[0] == 1045:
                    raise self.PerformVerifyAuthErrorException(e)
            else:
                logger.info('Результат проверки аутентификационных данных после выполнения шифрования: успех')
                conn.close()
                return

            time.sleep(1)
        logger.info('(Уведомление: Проверка информации для аутентификации может завершиться ошибкой из-за недоступности сети или тайм-аута соединения.)')
        raise self.InterruptException()
