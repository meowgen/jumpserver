from django.db import models
from django.utils.translation import gettext_lazy as _
from .base import BaseACL, BaseACLQuerySet
from common.utils import get_request_ip, get_ip_city
from common.utils.ip import contains_ip
from common.utils.time_period import contains_time_period
from common.utils.timezone import local_now_display


class ACLManager(models.Manager):

    def valid(self):
        return self.get_queryset().valid()


class LoginACL(BaseACL):
    class ActionChoices(models.TextChoices):
        reject = 'reject', _('Reject')
        allow = 'allow', _('Allow')
        confirm = 'confirm', _('Login confirm')

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, verbose_name=_('User'),
        related_name='login_acls'
    )
    rules = models.JSONField(default=dict, verbose_name=_('Rule'))
    action = models.CharField(
        max_length=64, verbose_name=_('Action'),
        choices=ActionChoices.choices, default=ActionChoices.reject
    )
    reviewers = models.ManyToManyField(
        'users.User', verbose_name=_("Reviewers"),
        related_name="login_confirm_acls", blank=True
    )
    objects = ACLManager.from_queryset(BaseACLQuerySet)()

    class Meta:
        ordering = ('priority', '-date_updated', 'name')
        verbose_name = _('Login acl')

    def __str__(self):
        return self.name

    @property
    def action_reject(self):
        return self.action == self.ActionChoices.reject

    @property
    def action_allow(self):
        return self.action == self.ActionChoices.allow

    @classmethod
    def filter_acl(cls, user):
        return user.login_acls.all().valid().distinct()

    @staticmethod
    def allow_user_confirm_if_need(user, ip):
        acl = LoginACL.filter_acl(user).filter(
            action=LoginACL.ActionChoices.confirm
        ).first()
        acl = acl if acl and acl.reviewers.exists() else None
        if not acl:
            return False, acl
        ip_group = acl.rules.get('ip_group')
        time_periods = acl.rules.get('time_period')
        is_contain_ip = contains_ip(ip, ip_group)
        is_contain_time_period = contains_time_period(time_periods)
        return is_contain_ip and is_contain_time_period, acl

    @staticmethod
    def allow_user_to_login(user, ip):
        acl = LoginACL.filter_acl(user).exclude(
            action=LoginACL.ActionChoices.confirm
        ).first()
        if not acl:
            return True, ''
        ip_group = acl.rules.get('ip_group')
        time_periods = acl.rules.get('time_period')
        is_contain_ip = contains_ip(ip, ip_group)
        is_contain_time_period = contains_time_period(time_periods)

        reject_type = ''
        if is_contain_ip and is_contain_time_period:
            allow = acl.action_allow
            if not allow:
                reject_type = 'ip' if is_contain_ip else 'time'
        else:
            allow = not acl.action_allow
            if not allow:
                reject_type = 'ip' if not is_contain_ip else 'time'

        return allow, reject_type

    def create_confirm_ticket(self, request):
        from tickets import const
        from tickets.models import ApplyLoginTicket
        from orgs.models import Organization
        title = _('Login confirm') + ' {}'.format(self.user)
        login_ip = get_request_ip(request) if request else ''
        login_ip = login_ip or '0.0.0.0'
        login_city = get_ip_city(login_ip)
        login_datetime = local_now_display()
        data = {
            'title': title,
            'type': const.TicketType.login_confirm,
            'applicant': self.user,
            'apply_login_city': login_city,
            'apply_login_ip': login_ip,
            'apply_login_datetime': login_datetime,
            'org_id': Organization.ROOT_ID,
        }
        ticket = ApplyLoginTicket.objects.create(**data)
        assignees = self.reviewers.all()
        ticket.open_by_system(assignees)
        return ticket
