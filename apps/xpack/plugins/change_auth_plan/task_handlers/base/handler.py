"""
执行改密计划的基类
"""
import time

from django.utils import timezone
from django.utils.translation import ugettext as _

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
                '\033[32m>>> 正在进行任务步骤 {}: {}\033[0m'
                ''.format(
                    handler.current_step, const.STEP_DESCRIBE_MAP[_step]
                )
            )

            if handler.is_frozen:
                # 如果任务被冻结，就不设置任务的 step
                logger.info(
                    '改密任务已被冻结，改密任务的执行步骤不再更新 '
                    '(step={}, describe={})'.format(
                        handler.task.step,
                        const.STEP_DESCRIBE_MAP[handler.task.step]
                    )
                )
            else:
                # 实时设置任务的step字段（防止服务宕机）
                logger.debug(
                    '实时更新改密任务的执行步骤 (describe={}{})'
                    ''.format(const.STEP_DESCRIBE_MAP[_step], _step)
                )
                handler.task.set_step(_step)

            # Print task start date
            time_start = time.time()
            if show_date:
                logger.info('步骤开始: {}'.format(local_now_display()))

            try:
                # 执行步骤
                return func(handler, *args, **kwargs)
            finally:
                # Print task finished date
                if show_date:
                    timedelta = round((time.time() - time_start), 2)
                    logger.info('步骤完成: 用时 {}s'.format(timedelta))
        return wrapper
    return decorator


class BaseChangePasswordHandler:
    def __init__(self, task, show_step_info=True):
        self.task = task
        self.conn = None
        self.retry_times = 3
        self.current_step = 0
        self.is_frozen = False  # 任务状态冻结标志
        self.show_step_info = show_step_info

    @staticmethod
    def log_error(msg):
        logger.error(wrapper_error(msg))

    def _step_perform_preflight_check(self):
        """
        执行改密前的条件检测
        请在相应子类中重写相应功能函数逻辑
        """
        raise NotImplementedError

    def _step_perform_change_auth(self):
        """
        执行改密
        请在相应子类中重写相应功能函数逻辑
        """
        raise NotImplementedError

    def _step_perform_verify_auth(self):
        """
        执行改密后对认证信息的校验
        请在相应子类中重写相应功能函数逻辑
        """
        raise NotImplementedError

    def show_task_steps_help_text(self):
        pass

    def _step_perform_keep_auth(self):
        """
        保存密码
        """
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
        logger.info('已完成对任务状态的更新')

    def _step_finished(self, is_success, reason, *args):
        if is_success:
            logger.info('任务执行成功')
        else:
            logger.error('任务执行失败')

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
        logger.info('说明: 改密任务执行的步骤如下:')
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
                logger.info('当前改密任务即将执行的步骤如下:')
                for index, step_method in enumerate(step_methods, 1):
                    logger.info('({}). {}'.format(
                        index, const.STEP_DESCRIBE_MAP[step_method['step']]
                    ))
            for index, step_method in enumerate(step_methods[:-2]):
                step_method['method']()
        except self.PerformPreflightCheckErrorException as e:
            error = str(e)
            logger.error(wrapper_error('改密任务执行提示: 执行改密前的条件检测不通过'))
        except self.PerformVerifyAuthErrorException as e:
            error = str(e)
            logger.error(wrapper_error('改密任务执行提示: 执行对改密后的认证信息校验失败'))
        except self.MultipleAttemptAfterErrorException:
            error = _('After many attempts to change the secret, it still failed')
            logger.error(wrapper_error('改密任务执行提示: 多次尝试改密后, 依然失败'))
        except self.InterruptException:
            error = '任务执行被系统中断 (step={})'.format(self.task.step)
            logger.error(wrapper_error('改密任务执行提示: 改密任务执行被系统主动中断'))
            logger.error(wrapper_error('为了保证当前改密任务再次启动时能够继续执行，任务状态将被冻结'))
            self.is_frozen = True
        except Exception as e:
            error = '任务执行被异常中断 (step={})'.format(self.task.step)
            logger.error(wrapper_error('改密任务执行提示: 改密任务执行由于出现异常被中断'))
            logger.error(wrapper_error('为了保证当前改密任务再次启动时能够继续执行，任务状态将被冻结'))
            self.is_frozen = True
            logger.error(wrapper_error('改密任务执行提示: 执行过程中出现异常信息: '))
            logger.info('下面打印发生异常的 Traceback 信息 : ')
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
        # 如果10分钟改密任务执行未完成，那么后续相同的任务进来，锁机制将失去意义
        lock = DistributedLock(lock_key, expire=10 * 60)
        logger.info('改密任务开始: {}'.format(local_now_display()))

        acquired = lock.acquire(timeout=10)
        if not acquired:
            logger.error('改密任务退出: 锁获取失败')
            return

        time_start = time.time()
        try:
            self._run()
        except Exception as e:
            self.log_error('改密任务运行出现异常: {}'.format(e))
            logger.error('下面显示异常 Traceback 信息: ')
            logger.error(e, exc_info=True)
        finally:
            logger.info('\n改密任务结束: {}'.format(local_now_display()))
            timedelta = round((time.time() - time_start), 2)
            logger.info('用时: {}'.format(timedelta))
            if lock.locked():
                lock.release()
