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
        logger.info('Условия обнаружения: системный пользователь {} к приложению {} возможность подключения'.format(
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
                f'\nРезультат теста: системный пользователь {self.task.system_user.username}\n'
                f' к приложению {self.task.app} не подключаемый'
            )
            logger.error('Причина: {}'.format(e))
            raise self.PerformPreflightCheckErrorException(e)
        else:
            logger.info(
                f'\nРезультат теста: системный пользователь {self.task.system_user.username}'
                f' к приложению {self.task.app} подключаемый'
            )
            self.conn = conn

    def _step_perform_change_auth(self):
        if self.conn is None:
            self.log_error('\nПожалуйста, выполните определение условий перед шифрованием')
        else:
            cur = self.conn.cursor()
            for i in range(self.retry_times):
                logger.info('Выполнить шифрование: попытка ({}/{}) раз'.format(i + 1, self.retry_times))
                try:
                    base_sql = f'alter login {self.task.system_user.username} with password=%s'
                    cur.execute(base_sql, self.task.password)
                    self.conn.commit()
                    self.task.system_user.password = self.task.password
                    self.task.system_user.save()
                except OperationalError as e:
                    logger.info('Выполнить результат расшифровки: провал')
                    logger.info('Причина: {}'.format(e))
                except Exception as e:
                    self.log_error(f'Результат выполнения ненормальный, причина: {e}')
                    break
                else:
                    logger.info('Выполнить результат расшифровки: успех')
                    break
            self.conn.close()

    def _step_perform_verify_auth(self):
        logger.info("(Примечание: Результат выполнения этого шага является признаком того, успешно ли завершена задача шифрования.)")
        for i in range(self.retry_times):
            logger.info('Проверка аутентификационных данных после изменения шифрования: попытка ({}/{}) раз'
                        ''.format(i + 1, self.retry_times))
            try:
                conn = pymssql.connect(
                    server=self.task.app.attrs.get('host'),
                    port=self.task.app.attrs.get('port'),
                    user=self.task.system_user.username,
                    password=self.task.password,
                )
            except OperationalError as e:
                logger.info('Результат проверки аутентификационных данных после выполнения шифрования: провал')
                self.log_error('Причина: {}'.format(e))
                if e.args[0][0] == 18456:
                    raise self.PerformVerifyAuthErrorException(e)
            else:
                logger.info('Результат проверки аутентификационных данных после выполнения шифрования: успех')
                conn.close()
                return

            time.sleep(1)
        logger.info('(Уведомление: Проверка информации для аутентификации может завершиться ошибкой из-за недоступности сети или тайм-аута соединения.)')
        raise self.InterruptException()
