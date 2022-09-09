# -*- coding: utf-8 -*-
#
import itertools
import uuid
from celery import current_task
from django.db import models
from django.utils.translation import ugettext_noop, ugettext_lazy as _

from applications.const import AppType, AppCategory
from common.utils import lazyproperty
from common.utils import get_logger

from .base import (
    BaseChangeAuthPlan,
    BaseChangeAuthPlanExecution,
    BaseChangeAuthPlanTask
)

logger = get_logger(__name__)
TASK_NAME_CHANGE_USER_PASSWORD = 'Change user password'


class ApplicationChangeAuthPlan(BaseChangeAuthPlan):
    category = models.CharField(
        max_length=16, choices=AppCategory.choices, verbose_name=_('Category')
    )
    type = models.CharField(
        max_length=16, choices=AppType.choices, verbose_name=_('Type')
    )
    apps = models.ManyToManyField(
        'applications.Application', related_name='change_auth_plans',
        verbose_name=_('Database')
    )
    system_users = models.ManyToManyField(
        'assets.SystemUser', related_name='change_app_auth_plans',
        verbose_name=_("System user")
    )

    recipients = models.ManyToManyField(
        'users.User', related_name='recipient_application_change_auth_plans', blank=True,
        verbose_name=_("Recipient")
    )

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('Application change auth plan')

    @lazyproperty
    def system_users_count(self):
        return self.system_users.count()

    @property
    def systemuser_display(self):
        return ', '.join(su.username for su in self.system_users.all())

    @property
    def protocol(self):
        return self.apps.type

    def get_register_task(self):
        from ..tasks import execute_app_change_auth_plan
        name = "execute_app_change_auth_plan_period_{}".format(str(self.id)[:8])
        task = execute_app_change_auth_plan.name
        args = (str(self.id), BaseChangeAuthPlanExecution.Trigger.timing)
        kwargs = {}
        return name, task, args, kwargs

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        apps = self.apps.all()
        system_users = self.system_users.all()
        attr_json.update({
            'app_ids': [str(app.id) for app in apps],
            'apps_display': [str(app) for app in apps],
            'system_user_ids': [str(su.id) for su in system_users],
            'system_users_display': [str(su) for su in system_users],
        })
        return attr_json

    def execute(self, trigger):
        try:
            hid = current_task.request.id
        except AttributeError:
            hid = str(uuid.uuid4())
        execution = ApplicationChangeAuthPlanExecution.objects.create(
            id=hid, plan=self, plan_snapshot=self.to_attr_json(),
            password=self.gen_execute_password(), trigger=trigger
        )
        return execution.start()


class ApplicationChangeAuthPlanExecution(BaseChangeAuthPlanExecution):
    plan = models.ForeignKey(
        ApplicationChangeAuthPlan, related_name='execution', on_delete=models.CASCADE,
        verbose_name=_('Application change auth plan')
    )

    class Meta:
        verbose_name = _('Application change auth plan execution')

    @property
    def username(self):
        return self.plan_snapshot.get('name')

    @property
    def apps_display(self):
        return self.plan_snapshot.get('apps_display')

    @property
    def system_users_display(self):
        return self.plan_snapshot.get('system_users_display')

    @property
    def apps_amount(self):
        return len(self.plan_snapshot.get('app_ids'))

    @property
    def system_users_amount(self):
        return len(self.plan_snapshot.get('system_user_ids'))

    @property
    def manager_name(self):
        return 'app'

    def create_plan_tasks(self):
        apps = self.plan.apps.all()
        system_users = self.plan.system_users.all()

        tasks = []
        for app, system_user in itertools.product(apps, system_users):
            task = ApplicationChangeAuthPlanTask.objects.create(
                app=app,
                system_user=system_user,
                password=self.get_password(),
                execution=self,
                type=self.plan.type,
            )
            tasks.append(task)
        return tasks


class ApplicationChangeAuthPlanTask(BaseChangeAuthPlanTask):
    app = models.ForeignKey(
        'applications.Application', on_delete=models.CASCADE, verbose_name=_('App')
    )
    system_user = models.ForeignKey(
        'assets.SystemUser', on_delete=models.CASCADE, verbose_name=_('System user')
    )
    execution = models.ForeignKey(
        ApplicationChangeAuthPlanExecution, related_name='task',
        on_delete=models.CASCADE, verbose_name=_('Application change auth plan execution')
    )
    type = models.CharField(max_length=16, default='mysql', verbose_name=_('Type'))

    class Meta:
        verbose_name = _('Application change auth plan task')

    def __str__(self):
        return '{}@{}'.format(self.system_user.username, self.app)

    @property
    def handler_name(self):
        return self.execution.plan.type

    @property
    def database_info(self):
        return {'id': str(self.app.id), 'name': self.app.name}

    @property
    def app_display(self):
        return self.app.name

    @property
    def system_user_display(self):
        return self.system_user.username

    def pre_start_check(self):
        error = None
        if not self.password or not self.password.strip():
            error = ugettext_noop('Password cannot be set to blank, exit. ')
        return error
