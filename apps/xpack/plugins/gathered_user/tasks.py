from celery import shared_task

from common.utils import get_object_or_none, get_logger
from orgs.utils import tmp_to_org, tmp_to_root_org
from .models import GatherUserTask, GatherUserTaskExecution

logger = get_logger(__file__)


@shared_task(queue='ansible')
def execute_gather_user_task(tid):
    with tmp_to_root_org():
        task = get_object_or_none(GatherUserTask, pk=tid)
    if not task:
        logger.error("No task found: {}".format(tid))
        return
    with tmp_to_org(task.org):
        task.execute()


@shared_task(queue='ansible')
def start_gather_user_execution(tid):
    with tmp_to_root_org():
        execution = get_object_or_none(GatherUserTaskExecution, pk=tid)
    if not execution:
        logger.error("No execution found: {}".format(tid))
        return
    with tmp_to_org(execution.org):
        execution.start()
