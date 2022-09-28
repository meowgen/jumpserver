import time

from django.utils import timezone
from django.utils.translation import gettext as _

from common.utils import get_logger
from common.utils.timezone import local_now_display
from common.utils.lock import DistributedLock
from xpack.plugins.change_auth_plan import const
from ...utils import wrapper_error


logger = get_logger(__file__)


def step(_step, show_date=True):
    def decorator(func):
        def wrapper(handler, *args, **kwargs):
            # Print step describe
            handler.current_step += 1
            logger.info(
                '\n'
                '\033[32m>>> Выполняется шаг задачи {}: {}\033[0m'
                ''.format(
                    handler.current_step, const.STEP_DESCRIBE_MAP[_step]
                )
            )

            if handler.is_frozen:
                logger.info(
                    'Задача шифрования заморожена, и этапы выполнения задачи шифрования больше не обновляются '
                    '(step={}, describe={})'.format(
                        handler.task.step,
                        const.STEP_DESCRIBE_MAP[handler.task.step]
                    )
                )
            else:
                logger.debug(
                    'Действия по обновлению и шифрованию в реальном времени (describe={}{})'
                    ''.format(const.STEP_DESCRIBE_MAP[_step], _step)
                )
                handler.task.set_step(_step)

            # Print task start date
            time_start = time.time()
            if show_date:
                logger.info('Пошаговое начало: {}'.format(local_now_display()))

            try:
                return func(handler, *args, **kwargs)
            finally:
                # Print task finished date
                if show_date:
                    timedelta = round((time.time() - time_start), 2)
                    logger.info('Шаг завершен: время {}сек'.format(timedelta))
        return wrapper
    return decorator


class BaseChangePasswordHandler:
    def __init__(self, task, show_step_info=True):
        self.task = task
        self.conn = None
        self.retry_times = 3
        self.current_step = 0
        self.is_frozen = False
        self.show_step_info = show_step_info

    @staticmethod
    def log_error(msg):
        logger.error(wrapper_error(msg))

    def _step_perform_preflight_check(self):
        raise NotImplementedError

    def _step_perform_change_auth(self):
        raise NotImplementedError

    def _step_perform_verify_auth(self):
        raise NotImplementedError

    def show_task_steps_help_text(self):
        pass

    def _step_perform_keep_auth(self):
        pass

    class PerformPreflightCheckErrorException(Exception):
        pass

    class PerformVerifyAuthErrorException(Exception):
        pass

    class MultipleAttemptAfterErrorException(Exception):
        pass

    class InterruptException(Exception):
        pass

    def _step_perform_task_update(self, is_success, reason, time_start):
        self.task.reason = reason[:1024]
        self.task.is_success = is_success
        self.task.timedelta = time.time() - time_start
        self.task.save()
        logger.info('Завершено обновление статуса задачи')

    def _step_finished(self, is_success, reason, *args):
        if is_success:
            logger.info('Задача выполнена успешно')
        else:
            logger.error('Не удалось выполнить задачу')

    @step(const.STEP_PERFORM_PREFLIGHT_CHECK)
    def step_perform_preflight_check(self):
        return self._step_perform_preflight_check()

    @step(const.STEP_PERFORM_CHANGE_AUTH)
    def step_perform_change_auth(self):
        return self._step_perform_change_auth()

    @step(const.STEP_PERFORM_VERIFY_AUTH)
    def step_perform_verify_auth(self):
        return self._step_perform_verify_auth()

    @step(const.STEP_PERFORM_KEEP_AUTH)
    def step_perform_keep_auth(self):
        return self._step_perform_keep_auth()

    @step(const.STEP_PERFORM_TASK_UPDATE)
    def step_perform_task_update(self, is_success, reason, time_start):
        return self._step_perform_task_update(is_success, reason, time_start)

    @step(const.STEP_FINISHED)
    def step_finished(self, is_success, reason, time_start):
        return self._step_finished(is_success, reason, time_start)

    def get_all_steps(self):
        step_methods = [
            {
                'step': const.STEP_PERFORM_PREFLIGHT_CHECK,
                'method': self.step_perform_preflight_check
            },
            {
                'step': const.STEP_PERFORM_CHANGE_AUTH,
                'method': self.step_perform_change_auth,
            },
            {
                'step': const.STEP_PERFORM_VERIFY_AUTH,
                'method': self.step_perform_verify_auth,
            },
            {
                'step': const.STEP_PERFORM_KEEP_AUTH,
                'method': self.step_perform_keep_auth,
            },
            {
                'step': const.STEP_PERFORM_TASK_UPDATE,
                'method': self.step_perform_task_update,
            },
            {
                'step': const.STEP_FINISHED,
                'method': self.step_finished,
            },
        ]
        return step_methods

    @classmethod
    def display_all_steps_info(cls):
        logger.info('Примечание. Шаги для выполнения задачи шифрования следующие:')
        self = cls(None)
        step_methods = self.get_all_steps()

        for index, step_method in enumerate(step_methods, 1):
            logger.info('({}). {}'.format(
                index, const.STEP_DESCRIBE_MAP[step_method['step']]
            ))

    def calculate_the_methods_of_step_to_be_performed(self):
        step_methods = self.get_all_steps()

        if self.task.step == const.STEP_PERFORM_CHANGE_AUTH:
            step_methods_to_performed = step_methods[1:]
        elif self.task.step == const.STEP_PERFORM_VERIFY_AUTH:
            step_methods_to_performed = step_methods[2:]
        elif self.task.step == const.STEP_PERFORM_KEEP_AUTH:
            step_methods_to_performed = step_methods[3:]
        else:
            step_methods_to_performed = step_methods
        return step_methods_to_performed

    def _run(self):
        time_start = time.time()
        self.task.date_start = timezone.now()
        self.task.save()

        is_success = False
        error = '-'
        try:
            step_methods = self.calculate_the_methods_of_step_to_be_performed()

            if self.show_step_info:
                logger.info('Шаги, которые необходимо выполнить в текущей задаче шифрования, следующие::')
                for index, step_method in enumerate(step_methods, 1):
                    logger.info('({}). {}'.format(
                        index, const.STEP_DESCRIBE_MAP[step_method['step']]
                    ))
            for index, step_method in enumerate(step_methods[:-2]):
                step_method['method']()
        except self.PerformPreflightCheckErrorException as e:
            error = str(e)
            logger.error(wrapper_error('Запрос на выполнение задачи шифрования: проверка условия перед выполнением модификации шифрования не удалась'))
        except self.PerformVerifyAuthErrorException as e:
            error = str(e)
            logger.error(wrapper_error('Запрос на выполнение задачи шифрования: не удалось проверить данные аутентификации после шифрования'))
        except self.MultipleAttemptAfterErrorException:
            error = _('After many attempts to change the secret, it still failed')
            logger.error(wrapper_error('Запрос на выполнение задачи шифрования: после нескольких попыток изменить пароль по-прежнему не удается'))
        except self.InterruptException:
            error = 'Выполнение задачи было прервано системой (step={})'.format(self.task.step)
            logger.error(wrapper_error('Запрос на выполнение задачи шифрования: выполнение задачи шифрования было активно прервано системой'))
            logger.error(wrapper_error('Чтобы гарантировать, что текущая задача шифрования может продолжать выполняться после ее перезапуска, статус задачи будет заморожен.'))
            self.is_frozen = True
        except Exception as e:
            error = 'Выполнение задачи было прервано аварийно (step={})'.format(self.task.step)
            logger.error(wrapper_error('Запрос на выполнение задачи шифрования: выполнение задачи шифрования было прервано из-за исключения'))
            logger.error(wrapper_error('Чтобы гарантировать, что текущая задача шифрования может продолжать выполняться после ее перезапуска, статус задачи будет заморожен.'))
            self.is_frozen = True
            logger.error(wrapper_error('Запрос на выполнение задачи шифрования: во время выполнения появилось сообщение об исключении:'))
            logger.info('Следующее выводит информацию о трассировке исключения:')
            logger.error(e, exc_info=True)
        else:
            is_success = True
        finally:
            if error.startswith('Invalid/incorrect password'):
                reason = _('Invalid/incorrect password')
            elif error.startswith('Failed to connect to the host'):
                reason = _('Failed to connect to the host')
            elif error.startswith('Data could not be sent to remote'):
                reason = _('Data could not be sent to remote')
            else:
                reason = error
            self.step_perform_task_update(is_success, reason, time_start)
            self.step_finished(is_success, reason, time_start)

    def get_lock_key(self):
        raise NotImplementedError()

    def run(self):
        lock_key = self.get_lock_key()
        lock = DistributedLock(lock_key, expire=10 * 60)
        logger.info('Начинается задача расшифровки: {}'.format(local_now_display()))

        acquired = lock.acquire(timeout=10)
        if not acquired:
            logger.error('Выход из задачи шифрования: не удалось получить блокировку')
            return

        time_start = time.time()
        try:
            self._run()
        except Exception as e:
            self.log_error('Исключение возникает при выполнении задачи шифрования: {}'.format(e))
            logger.error('Ниже показана информация об исключении Traceback.: ')
            logger.error(e, exc_info=True)
        finally:
            logger.info('\nЗадача шифрования завершена: {}'.format(local_now_display()))
            timedelta = round((time.time() - time_start), 2)
            logger.info('Время: {}'.format(timedelta))
            if lock.locked():
                lock.release()
