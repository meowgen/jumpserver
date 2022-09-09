# -*- coding: utf-8 -*-
#
from celery import shared_task

from common.utils import get_object_or_none, get_logger, combine_seq
from orgs.utils import tmp_to_org, tmp_to_root_org
from .models import (
    ChangeAuthPlan,
    ChangeAuthPlanTask,
    ApplicationChangeAuthPlan,
    ApplicationChangeAuthPlanTask
)

logger = get_logger(__file__)


@shared_task(queue='ansible')
def execute_change_auth_plan(pid, trigger):
    with tmp_to_root_org():
        plan = get_object_or_none(ChangeAuthPlan, pk=pid)
    if not plan:
        logger.error("No change auth plan found: {}".format(pid))
        return
    with tmp_to_org(plan.org):
        plan.execute(trigger)


@shared_task(queue='ansible')
def start_change_auth_task(tid):
    with tmp_to_root_org():
        task = get_object_or_none(ChangeAuthPlanTask, pk=tid)
    if not task:
        logger.error("No change auth plan task found: {}".format(tid))
        return
    with tmp_to_org(task.org):
        task.start()


@shared_task
def execute_app_change_auth_plan(pid, trigger):
    with tmp_to_root_org():
        plan = get_object_or_none(ApplicationChangeAuthPlan, pk=pid)
    if not plan:
        logger.error("No app change auth plan found: {}".format(pid))
        return
    with tmp_to_org(plan.org):
        plan.execute(trigger)


@shared_task
def start_app_change_auth_task(tid):
    with tmp_to_root_org():
        task = get_object_or_none(ApplicationChangeAuthPlanTask, pk=tid)
    if not task:
        logger.error("No app change auth plan task found: {}".format(tid))
        return
    with tmp_to_org(task.org):
        task.start()


@shared_task(soft_time_limit=10 * 60)
def test_change_auth_plan_task_connectivity(
        plan=None, execution=None, task=None,
        asset=None, username=None, keep_auth_to_authbook=True
):
    from .models import ChangeAuthPlanTask
    from assets.tasks import test_user_connectivity

    with tmp_to_root_org():
        queryset = ChangeAuthPlanTask.objects.all().order_by('-date_start')

        if plan is not None:
            executions = plan.execution.all()
            queryset = queryset.filter(execution__in=executions)
        if execution is not None:
            queryset = queryset.filter(execution=execution)
        if task is not None:
            queryset = queryset.filter(id=task.id)
        if asset is not None:
            queryset = queryset.filter(asset=asset)
        if username is not None:
            queryset = queryset.filter(username=username)

        total = queryset.count()
        for index, q in enumerate(queryset):
            print('{} 测试进度: ({}/{})'.format('>' * 10, index + 1, total))
            task_name = '测试改密计划任务的可连接性: {}'.format(q)
            print('{}@{} => execution: {}, plan: {}|{}'.format(
                q.username, q.asset, q.execution.id, q.execution.plan.id,
                q.execution.plan.name
            ))
            raw, summary = test_user_connectivity(
                task_name, username=q.username, asset=q.asset,
                password=q.password
            )
            dark = summary.get('dark')
            if dark:
                logger.info('测试任务中认证信息的可连接性: 失败')
                continue
            logger.info('测试任务中认证信息的可连接性: 成功')
            if keep_auth_to_authbook:
                logger.info('重新尝试将认证信息设置为最新的状态')
                with tmp_to_org(q.org):
                    q.retry_keep_auth_to_authbook()


def handle_interrupt_change_auth_plan_tasks():
    """
    处理被中断的改密任务
    """
    with tmp_to_root_org():
        asset_tasks = ChangeAuthPlanTask.get_interrupted_tasks()
        database_tasks = ApplicationChangeAuthPlanTask.get_interrupted_tasks()
        tasks = combine_seq(asset_tasks, database_tasks)

        logger.info("Get need handle interrupt change auth plan tasks "
                    "(count: {})\n".format(asset_tasks.count()))
        logger.info("Get need handle interrupt app change auth plan tasks "
                    "(count: {})\n".format(database_tasks.count()))

        for task in tasks:
            with tmp_to_org(task.org):
                task.start()

# * 为防止出现其他不可预测的问题，先行取消任务的定时处理计划: `定时处理被中断的改密任务`
# @shared_task
# @after_app_ready_start
# def handle_be_interrupted_change_auth_tasks_periodic():
#     tasks = {
#         'handle_be_interrupted_change_auth_task_periodic': {
#             'task': handle_interrupt_change_auth_plan_tasks.name,
#             'interval': None,
#             'crontab': '*/60 * * * *',
#             'enabled': True,
#         }
#     }
#     create_or_update_celery_periodic_tasks(tasks)
