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
            f'Условия обнаружения: системный пользователь {self.task.system_user.username} '
            f'к приложению {self.task.app} возможность подключения'
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
                f'\nРезультат теста: системный пользователь {self.task.system_user.username}'
                f' к приложению {self.task.app} не подключаемый'
            ))
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
                logger.info('Выполнить шифрование: попытка ({}/{}) раз'
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
                    logger.info('Выполнить результат расшифровки: провал')
                    logger.info('Причина: {}'.format(e))
                except Exception as e:
                    self.log_error(f'Результат выполнения ненормальный, причина: {e}')
                    break
                else:
                    logger.info('Выполнить результат расшифровки: успех')
                    cur.close()
                    self.conn.close()
                    return
            cur.close()
            self.conn.close()
            raise self.MultipleAttemptAfterErrorException()

    def _step_perform_verify_auth(self):
        logger.info("(Примечание: Результат выполнения этого шага является признаком того, успешно ли завершена задача шифрования.)")
        for i in range(self.retry_times):
            logger.info('Проверка аутентификационных данных после изменения шифрования: попытка ({}/{}) раз'
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
                logger.info('Результат проверки аутентификационных данных после выполнения шифрования: провал')
                logger.error('Причина: {}'.format(e))
                if 'password authentication' in e.args[0]:
                    raise self.PerformVerifyAuthErrorException(e)
            else:
                logger.info('Результат проверки аутентификационных данных после выполнения шифрования: успех')
                conn.close()
                return

            time.sleep(1)
        logger.info('(Уведомление: Проверка информации для аутентификации может завершиться ошибкой из-за недоступности сети или тайм-аута соединения.)')
        raise self.InterruptException()
