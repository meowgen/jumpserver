# -*- coding: utf-8 -*-
#

import boto3
from django.utils.translation import ugettext_lazy as _
from .base import BaseProvider

# Region
# https://docs.aws.amazon.com/zh_cn/AWSEC2/latest/UserGuide/using-regions-availability-zones.html

# Instance attributes
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#vpc


regions_mapping = {
    # AWS 中国
    'cn-north-1': _('China (Beijing)'),
    'cn-northwest-1': _('China (Ningxia)'),

    # AWS 国际
    'us-east-2': _('US East (Ohio)'),
    'us-east-1': _('US East (N. Virginia)'),
    'us-west-1': _('US West (N. California)'),
    'us-west-2': _('US West (Oregon)'),
    'af-south-1': _('Africa (Cape Town)'),
    'ap-east-1': _('Asia Pacific (Hong Kong)'),
    'ap-south-1': _('Asia Pacific (Mumbai)'),
    'ap-northeast-3': _('Asia Pacific (Osaka-Local)'),
    'ap-northeast-2': _('Asia Pacific (Seoul)'),
    'ap-southeast-1': _('Asia Pacific (Singapore)'),
    'ap-southeast-2': _('Asia Pacific (Sydney)'),
    'ap-northeast-1': _('Asia Pacific (Tokyo)'),
    'ca-central-1': _('Canada (Central)'),
    'eu-central-1': _('Europe (Frankfurt)'),
    'eu-west-1': _('Europe (Ireland)'),
    'eu-west-2': _('Europe (London)'),
    'eu-south-1': _('Europe (Milan)'),
    'eu-west-3': _('Europe (Paris)'),
    'eu-north-1': _('Europe (Stockholm)'),
    'me-south-1': _('Middle East (Bahrain)'),
    'sa-east-1': _('South America (São Paulo)'),
}


class Provider(BaseProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session = boto3.Session(aws_access_key_id=self.ak, aws_secret_access_key=self.secret)

    def _is_valid(self):
        self.get_instances_of_region(region_id='us-east-1')

    def get_regions(self):
        region_ids = self.get_region_ids()
        regions = {region_id: regions_mapping.get(region_id, region_id) for region_id in region_ids}
        return regions

    def get_region_ids(self):
        region_ids = self.session.get_available_regions(service_name='ec2')
        return region_ids

    def get_instances_of_region(self, region_id):
        ec2 = self.session.resource(service_name='ec2', region_name=region_id)
        instances = list(ec2.instances.all())
        return instances

    def _preset_instance_properties(self, instance):
        # name
        tags = instance.tags or []
        names = [tag['Value'] for tag in tags if tag['Key'] == 'Name']
        name = names[0] if len(names) > 0 else None

        setattr(instance, 'name', name)

    def get_instance_id(self, instance):
        return instance.id

    def get_instance_name(self, instance):
        return getattr(instance, 'name')

    def get_instance_platform(self, instance):
        return instance.platform

    def get_instance_private_ips(self, instance):
        return [instance.private_ip_address] if instance.private_ip_address else []

    def get_instance_public_ip(self, instance):
        return instance.public_ip_address

    def get_instance_region_id(self, instance):
        return getattr(instance, 'region_id')

    def get_instance_vpc_id(self, instance):
        return instance.vpc_id
