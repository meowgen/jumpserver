# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from common.drf.serializers import MethodSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import Account
from .. import const
from .account_attrs import (
    AccessKeySerializer, AzureAttrsSerializer, VMwareAttrsSerializer,
    NutanixAttrsSerializer, HuaweiPrivateAttrsSerializer, QingyunPrivateAttrsSerializer,
    OpenStackAttrsSerializer, GCPAttrsSerializer, FusionComputeAttrSerializer

)

__all__ = ['AccountSerializer']

attrs_provider_serializer_classes_mapping = {
    # ak/sk
    const.ProviderChoices.aliyun: AccessKeySerializer,
    const.ProviderChoices.aws_china: AccessKeySerializer,
    const.ProviderChoices.aws_international: AccessKeySerializer,
    const.ProviderChoices.huaweicloud: AccessKeySerializer,
    const.ProviderChoices.baiducloud: AccessKeySerializer,
    const.ProviderChoices.qcloud: AccessKeySerializer,
    const.ProviderChoices.jdcloud: AccessKeySerializer,
    # other
    const.ProviderChoices.azure: AzureAttrsSerializer,
    const.ProviderChoices.azure_international: AzureAttrsSerializer,
    const.ProviderChoices.vmware: VMwareAttrsSerializer,
    const.ProviderChoices.nutanix: NutanixAttrsSerializer,
    const.ProviderChoices.huaweicloud_private: HuaweiPrivateAttrsSerializer,
    const.ProviderChoices.qingcloud_private: QingyunPrivateAttrsSerializer,
    const.ProviderChoices.openstackcloud: OpenStackAttrsSerializer,
    const.ProviderChoices.gcp: GCPAttrsSerializer,
    const.ProviderChoices.fc: FusionComputeAttrSerializer,
}


# Account Serializer
class AccountSerializer(BulkOrgResourceModelSerializer):
    provider_display = serializers.ReadOnlyField(source='get_provider_display')
    validity_display = serializers.ReadOnlyField(source='get_validity_display')
    attrs = MethodSerializer()

    class Meta:
        model = Account
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'attrs', 'provider', 'provider_display', 'validity',
            'validity_display', 'comment', 'date_created', 'created_by',
        ]
        fields = fields_small
        read_only_fields = [
            'date_created', 'created_by', 'validity'
        ]
        ref_name = 'CloudAccountSerializer'
        extra_kwargs = {
            'attrs': {'label': _("Attrs")},
            'validity_display': {'label': _('Validity display')},
            'provider_display': {'label': _('Provider display')}
        }

    @property
    def _provider(self):
        if isinstance(self.instance, Account):
            _provider = self.instance.provider
        else:
            _provider = self.context['request'].query_params.get('provider')
        return _provider

    def get_attrs_serializer(self):
        default_serializer = serializers.Serializer(read_only=True)

        if self._provider:
            serializer_class = attrs_provider_serializer_classes_mapping.get(self._provider)
        else:
            serializer_class = default_serializer

        if not serializer_class:
            serializer_class = default_serializer

        if isinstance(serializer_class, type):
            serializer = serializer_class()
        else:
            serializer = serializer_class
        return serializer

    def validate_attrs(self, attrs):
        _attrs = self.instance.attrs if self.instance else {}
        _attrs.update(attrs)
        return _attrs
