# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from django.db.models import TextChoices, IntegerChoices


class ProviderChoices(TextChoices):
    aliyun = 'aliyun', _('Alibaba Cloud')
    aws_international = 'aws_international', _('AWS (International)')
    aws_china = 'aws_china', _('AWS (China)')
    azure = 'azure', _('Azure (China)')
    azure_international = 'azure_international', _('Azure (International)')
    huaweicloud = 'huaweicloud', _('Huawei Cloud')
    baiducloud = 'baiducloud', _('Baidu Cloud')
    jdcloud = 'jdcloud', _('JD Cloud')
    qcloud = 'qcloud', _('Tencent Cloud')
    vmware = 'vmware', _('VMware')
    nutanix = 'nutanix', _('Nutanix')
    huaweicloud_private = 'huaweicloud_private', _('Huawei Private Cloud')
    qingcloud_private = 'qingcloud_private', _('Qingyun Private Cloud')
    openstackcloud = 'openstack', _('OpenStack')
    gcp = 'gcp', _('Google Cloud Platform')
    fc = 'fc', _('Fusion Compute')


class HostnameStrategyChoices(TextChoices):
    instance_name = 'instance_name', _('Instance name')
    instance_name_partial_ip = 'instance_name_partial_ip', _('Instance name and Partial IP')


class ExecutionStatusChoices(IntegerChoices):
    failed = 0, _('Failed')
    succeed = 1, _('Succeed')


class InstanceStatusChoices(IntegerChoices):
    unsync = 0, _('Unsync')
    sync = 1, _('New Sync')
    exist = 2, _('Synced')
    released = 3, _('Released')
