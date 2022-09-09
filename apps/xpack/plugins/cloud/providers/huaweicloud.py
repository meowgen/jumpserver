# -*- coding: utf-8 -*-
import uuid
from hashlib import md5

from django.utils.translation import ugettext_lazy as _
from openstack import connection

from common.utils import lazyproperty
from .base import BaseProvider


# Regions
# https://developer.huaweicloud.com/en-us/endpoint

# Instance attributes
# https://support.huaweicloud.com/api-ecs/ecs_05_0002.html


class Provider(BaseProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conn = connection.Connection(cloud='myhuaweicloud.com', ak=self.ak, sk=self.secret)
        # 存放所有镜像id和platform的映射
        self.image_platform_mapping = {}
        # 存放当前账户所有的 vpcs
        self.vpcs = []
        self.page_size = 20

    def _is_valid(self):
        list(self.conn.identity.projects())

    def get_regions(self):
        # TODO: Get regions by api
        regions = {
            'af-south-1': _('AF-Johannesburg'),
            'cn-north-4': _('CN North-Beijing4'),
            'cn-north-1': _('CN North-Beijing1'),
            'cn-east-2': _('CN East-Shanghai2'),
            'cn-east-3': _('CN East-Shanghai1'),
            'cn-south-1': _('CN South-Guangzhou'),
            'na-mexico-1': _('LA-Mexico City1'),
            'la-south-2': _('LA-Santiago'),
            'sa-brazil-1': _('LA-Sao Paulo1'),
            'eu-west-0': _('EU-Paris'),
            'cn-southwest-2': _('CN Southwest-Guiyang1'),
            'ap-southeast-2': _('AP-Bangkok'),
            'ap-southeast-3': _('AP-Singapore'),
            'ap-southeast-1': _('CN-Hong Kong'),

            'cn-northeast-1': _('CN Northeast-Dalian'),
            'cn-north-9': _('CN North-Ulanqab1'),
            'cn-south-4': _('CN South-Guangzhou-InvitationOnly')
        }
        return regions

    def prefetch_vpcs(self):
        vpcs = list(self.conn.vpcv1.vpcs(paginated=False))
        self.vpcs.extend(vpcs)

    @lazyproperty
    def projects(self):
        projects = self.conn.identity.projects()
        projects_mapping = {project.name: project.id for project in projects}
        return projects_mapping

    def set_current_region(self, region_id):
        project_id = self.projects.get(region_id)
        if not project_id:
            return None
        self.conn.session.project_id = project_id
        self.conn.session.region = region_id

    def get_instances_of_region(self, region_id):
        self.set_current_region(region_id)
        self.prefetch_vpcs()
        servers = list(self.conn.compute.servers(limit=self.page_size))
        return servers

    def _preset_instance_properties(self, instance):
        # platform
        image_id = instance.image.get('id', '')
        platform = self.image_platform_mapping.get(image_id)
        if not platform:
            try:
                image = self.conn.image.get_image(image_id)
            except Exception as e:
                print(f'Get image error with id {image_id}: {e}')
                image = None
            if image:
                platform = image.os_type
            else:
                platform = 'linux'
            self.image_platform_mapping[image_id] = platform
        # private ip
        address = list(instance.addresses.values())
        if address and address[0]:
            private_ips = [address[0][0].get('addr')]
        else:
            private_ips = []
        # public ip
        if address and address[0] and len(address[0]) == 2:
            public_ip = address[0][1].get("addr")
        else:
            public_ip = None
        # vpc id
        vpc_id = 'default'
        vpc_ids = list(instance.addresses.keys())
        for vpc in self.vpcs:
            for _vpc_id in vpc_ids:
                if _vpc_id == vpc.id:
                    vpc_id = vpc.name
                    break
        print('[DEBUG] vpcs: {}, vpc_ids: {}'.format([vpc.id for vpc in self.vpcs], vpc_ids))
        # set
        setattr(instance, 'platform', platform)
        setattr(instance, 'private_ips', private_ips)
        setattr(instance, 'public_ip', public_ip)
        setattr(instance, 'vpc_id', vpc_id)

    def get_instance_id(self, instance):
        return instance.id

    def get_instance_name(self, instance):
        return instance.name

    def get_instance_platform(self, instance):
        return getattr(instance, 'platform')

    def get_instance_private_ips(self, instance):
        return getattr(instance, 'private_ips')

    def get_instance_public_ip(self, instance):
        return getattr(instance, 'public_ip')

    def get_instance_region_id(self, instance):
        return getattr(instance, 'region_id')

    def get_instance_vpc_id(self, instance):
        return getattr(instance, 'vpc_id')
