# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.drf.fields import EncryptedField


# Account attrs Serializer


class AccessKeySerializer(serializers.Serializer):
    """ AK/SK """
    access_key_id = serializers.CharField(
        max_length=128, required=False, label=_('Access key id')
    )
    access_key_secret = EncryptedField(
        max_length=128, required=False, label=_('Access key secret')
    )


class UsernamePasswordSerializer(serializers.Serializer):
    """ Username/Password """
    username = serializers.CharField(max_length=128, required=True, label=_('Username'))
    password = EncryptedField(
        max_length=128, required=False, allow_blank=True, label=_('Password')
    )


class AzureAttrsSerializer(serializers.Serializer):
    """ Azure """
    client_id = serializers.CharField(
        max_length=128, required=False, label=_('Client ID')
    )
    client_secret = EncryptedField(
        max_length=128, required=False, label=_('Client Secret')
    )
    tenant_id = serializers.CharField(
        max_length=128, required=False, label=_('Tenant ID')
    )
    subscription_id = serializers.CharField(
        max_length=128, required=False, label=_('Subscription ID')
    )

    def validate(self, attrs):
        # 如果不校验后台创建Azure Client时会500
        if self.parent.instance:
            return attrs
        errors_required_fields = []
        to_validated_fields = ['client_id', 'client_secret', 'tenant_id', 'subscription_id']
        for field in to_validated_fields:
            if not attrs.get(field):
                errors_required_fields.append(field)
        errors = {field: _('This field is required.') for field in errors_required_fields}
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class NutanixAttrsSerializer(AccessKeySerializer):
    """ Nutanix """
    api_endpoint = serializers.CharField(
        max_length=128, required=True, label='API Endpoint',
        help_text="eg. https://IP:9440/api/nutanix/v3/"
    )


class VMwareAttrsSerializer(UsernamePasswordSerializer):
    """ VMware """
    host = serializers.CharField(max_length=128, required=True, label=_('Host'))
    port = serializers.IntegerField(default=443, label=_('Port'))

    def validate(self, attrs):
        password = attrs.get('password')
        if not password:
            attrs.pop('password', None)
        return attrs


class HuaweiPrivateAttrsSerializer(serializers.Serializer):
    """ Huawei Private Cloud Platform"""
    sc_username = serializers.CharField(max_length=128, required=True, label=f"SC {_('Username')}")
    sc_password = EncryptedField(
        max_length=128, required=True, label=f"SC {_('Password')}"
    )
    domain_name = serializers.CharField(
        max_length=128, required=True, label=f"SC {_('domain_name')}"
    )
    oc_username = serializers.CharField(max_length=128, required=True, label=f"OC {_('Username')}")
    oc_password = EncryptedField(
        max_length=128, required=True, label=f"OC {_('Password')}"
    )
    api_endpoint = serializers.CharField(max_length=128, required=True, label=_('API Endpoint'))


class QingyunPrivateAttrsSerializer(AccessKeySerializer):
    """ Qingyun Private Cloud Platform"""
    api_endpoint = serializers.CharField(max_length=128, required=True, label=_('API Endpoint'))


class OpenStackAttrsSerializer(UsernamePasswordSerializer):
    """ OpenStack Private Cloud Platform"""
    auth_url = serializers.CharField(
        max_length=128, required=True, label=_('Auth url'),
        help_text=_('eg: http://openstack.example.com:5000/v3')
    )
    user_domain_name = serializers.CharField(
        max_length=128, required=True, label=_('User domain')
    )


class GCPAttrsSerializer(serializers.Serializer):
    """ Google Cloud Platform """
    service_account_key = serializers.DictField(
        write_only=True, required=False, label=_('Service account key'),
        help_text=_('The file is in JSON format')
    )


class FusionComputeAttrSerializer(UsernamePasswordSerializer):
    """ Fusion Compute Private Cloud"""
    api_endpoint = serializers.CharField(max_length=128, required=True, label=_('API Endpoint'))
