import uuid
from django.db import models
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from orgs.mixins.models import OrgModelMixin
from common.utils import lazyproperty, get_logger
from common.utils.translate import translate_value
from common.db.fields import (
    EncryptCharField,
    JsonDictCharField,
    JsonDictTextField
)
from ops.mixin import PeriodTaskModelMixin

from .. import const

logger = get_logger(__name__)


class BaseChangeAuthPlan(PeriodTaskModelMixin, OrgModelMixin):
    PASSWORD_CUSTOM = "custom"
    PASSWORD_RANDOM_ONE = 'random_one'
    PASSWORD_RANDOM_ALL = 'random_all'

    PASSWORD_STRATEGY_CHOICES = (
        (PASSWORD_CUSTOM, _('Custom password')),
        (PASSWORD_RANDOM_ONE, _('All assets use the same random password')),
        (PASSWORD_RANDOM_ALL, _('All assets use different random password')),
    )

    password_strategy = models.CharField(
        max_length=128, blank=True, null=True,
        choices=PASSWORD_STRATEGY_CHOICES,
        verbose_name=_('Password strategy')
    )
    password_rules = JsonDictCharField(
        max_length=2048, blank=True, null=True,
        verbose_name=_('Password rules')
    )
    password = EncryptCharField(
        max_length=256, blank=True, null=True, verbose_name=_('Password')
    )
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    created_by = models.CharField(
        max_length=128, null=True, verbose_name=_('Created by')
    )

    def __str__(self):
        return self.name + '@' + str(self.created_by)

    class Meta:
        abstract = True

    @lazyproperty
    def run_times(self):
        return self.execution.count()

    @property
    def password_custom(self):
        return self.password_strategy == self.PASSWORD_CUSTOM

    @property
    def password_random_one(self):
        return self.password_strategy == self.PASSWORD_RANDOM_ONE

    @property
    def password_random_all(self):
        return self.password_strategy == self.PASSWORD_RANDOM_ALL

    def gen_execute_password(self):
        if self.password_custom:
            return self.password
        elif self.password_random_one:
            from ..utils import generate_random_password
            return generate_random_password(**self.password_rules)
        else:
            return None

    def to_attr_json(self):
        return {
            'name': self.name,
            'is_periodic': self.is_periodic,
            'interval': self.interval,
            'crontab': self.crontab,
            'password_strategy': self.password_strategy,
            'password_rules': self.password_rules,
            'date_created': str(self.date_created),
            'date_updated': str(self.date_updated),
            'created_by': self.created_by,
            'comment': self.comment,
            'org_id': self.org_id,
            'recipients': {
                str(recipient.id): (str(recipient), bool(recipient.secret_key))
                for recipient in self.recipients.all()
            }
        }


class BaseChangeAuthPlanExecution(OrgModelMixin):
    plan: BaseChangeAuthPlan
    task: models.Manager

    class Trigger(models.TextChoices):
        manual = 'manual', _('Manual trigger')
        timing = 'timing', _('Timing trigger')

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    date_start = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Date start')
    )
    timedelta = models.FloatField(
        default=0.0, verbose_name=_('Time'), null=True
    )
    plan_snapshot = JsonDictTextField(
        blank=True, null=True, verbose_name=_('Change auth plan snapshot')
    )
    password = EncryptCharField(
        max_length=256, blank=True, null=True, verbose_name=_('Password')
    )
    trigger = models.CharField(
        max_length=128, default=Trigger.manual, choices=Trigger.choices,
        verbose_name=_('Trigger mode')
    )
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    @property
    def password_strategy(self):
        return self.plan_snapshot.get('password_strategy')

    @property
    def get_password_strategy_display(self):
        password_strategy_choices = dict(self.plan.PASSWORD_STRATEGY_CHOICES)
        return password_strategy_choices.get(self.password_strategy)

    @property
    def password_random_all(self):
        return self.password_strategy == self.plan.PASSWORD_RANDOM_ALL

    @property
    def result_summary(self):
        succeed = failed = 0
        result = self.task.all().values('is_success').order_by('is_success') \
            .annotate(count=Count('is_success'))
        for r in result:
            if r['is_success']:
                succeed = r['count']
            else:
                failed = r['count']
        return {'total': succeed + failed, 'succeed': succeed, 'failed': failed}

    @property
    def recipients(self):
        recipients = self.plan_snapshot.get('recipients')
        if not recipients:
            return []
        return recipients.values()

    def get_password(self):
        if self.password_random_all:
            from ..utils import generate_random_password
            password_rules = self.plan_snapshot.get('password_rules')
            return generate_random_password(**password_rules)
        else:
            return self.password

    def create_plan_tasks(self):
        return []

    @property
    def manager_name(self):
        raise NotImplemented()

    def start(self):
        from ..task_handlers import ExecutionManager
        manager = ExecutionManager(execution=self)
        return manager.run()


class BaseChangeAuthPlanTask(OrgModelMixin):
    STEP_STATUS_CHOICE = (
        (const.STEP_READY, _('Ready')),
        (const.STEP_PERFORM_PREFLIGHT_CHECK, _('Preflight check')),
        (const.STEP_PERFORM_CHANGE_AUTH, _('Change auth')),
        (const.STEP_PERFORM_VERIFY_AUTH, _('Verify auth')),
        (const.STEP_PERFORM_KEEP_AUTH, _('Keep auth')),
        (const.STEP_FINISHED, _('Finished'))
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    password = EncryptCharField(
        max_length=256, blank=True, null=True, verbose_name=_('Password')
    )
    step = models.SmallIntegerField(
        default=const.STEP_READY, choices=STEP_STATUS_CHOICE, verbose_name=_('Step')
    )
    reason = models.CharField(max_length=1024, blank=True, null=True, verbose_name=_('Reason'))
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Date start'))
    timedelta = models.FloatField(default=0.0, null=True, verbose_name=_('Time'))

    class Meta:
        abstract = True

    @classmethod
    def get_interrupted_tasks(cls):
        return cls.objects.exclude(step__in=[const.STEP_READY, const.STEP_FINISHED])

    def set_step(self, step):
        self.step = step
        self.save()

    @property
    def reason_display(self):
        value = translate_value(self.reason)
        return value

    @property
    def handler_name(self):
        raise NotImplemented()

    def pre_start_check(self):
        raise NotImplemented()

    def start(self, show_step_info=True):
        error = self.pre_start_check()
        if error:
            self.reason = error
            self.save()
            error = translate_value(error)
            logger.error(error)
            return
        from ..task_handlers import TaskHandler
        handler = TaskHandler(task=self, show_step_info=show_step_info)
        return handler.run()
