from django.utils.translation import gettext as _
from rest_framework import serializers

from assets.serializers.utils import validate_password_for_ansible
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ops.mixin import PeriodTaskSerializerMixin
from common.utils import get_logger
from common.drf.fields import EncryptedField

from ..const import DEFAULT_PASSWORD_RULES

logger = get_logger(__file__)

__all__ = [
    'BasePlanSerializer', 'BaseExecutionSerializer'
]


class BasePlanSerializer(PeriodTaskSerializerMixin, BulkOrgResourceModelSerializer):
    password = EncryptedField(
        label=_('Password'), required=False, allow_blank=True,
        allow_null=True, max_length=256, write_only=True,
        validators=[validate_password_for_ansible]
    )
    password_rules = serializers.DictField(default=DEFAULT_PASSWORD_RULES)
    password_strategy_display = serializers.ReadOnlyField(
        source='get_password_strategy_display', label=_('Password strategy')
    )

    class Meta:
        fields = [
            'id', 'name', 'is_periodic', 'interval', 'crontab', 'password_strategy',
            'password_rules', 'password', 'comment', 'run_times', 'date_created',
            'date_updated', 'created_by', 'password_strategy_display', 'periodic_display',
            'recipients'
        ]
        read_only_fields = (
            'date_created', 'date_updated', 'created_by', 'run_times',
            'periodic_display', 'password_strategy_display',
        )
        extra_kwargs = {
            'name': {'required': True},
            'periodic_display': {'label': _('Periodic perform')},
            'run_times': {'label': _('Run times')},
            'recipients': {'label': _('Recipient'), 'help_text': _(
                "Currently only mail sending is supported"
            )},
        }

    def validate_password_rules(self, password_rules):
        length = password_rules.get('length')
        symbol_set = password_rules.get('symbol_set', '')

        try:
            length = int(length)
        except Exception as e:
            logger.error(e)
            msg = _("* Please enter the correct password length")
            raise serializers.ValidationError(msg)
        if length < 6 or length > 30:
            msg = _('* Password length range 6-30 bits')
            raise serializers.ValidationError(msg)

        if not isinstance(symbol_set, str):
            symbol_set = str(symbol_set)

        password_rules = {'length': length, 'symbol_set': ''.join(symbol_set)}
        return password_rules


class BaseExecutionSerializer(serializers.ModelSerializer):
    password = EncryptedField(
        label=_('Password'), required=False, allow_blank=True,
        allow_null=True, max_length=256
    )
    password_strategy_display = serializers.ReadOnlyField(source='get_password_strategy_display')
    trigger_display = serializers.ReadOnlyField(
        source='get_trigger_display', label=_('Trigger mode')
    )

    class Meta:
        read_only_fields = (
            'id', 'plan_snapshot', 'date_start', 'timedelta', 'date_created'
        )
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True},
        }
