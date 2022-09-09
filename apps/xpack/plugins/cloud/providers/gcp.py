# -*- coding: utf-8 -*-
#

from collections import defaultdict
from google.cloud.compute_v1.services.instances import InstancesClient
from google.cloud.compute_v1.services.regions import RegionsClient
from google.cloud.compute_v1.services.zones import ZonesClient
from google.cloud.compute_v1.services.disks import DisksClient
from common.utils import lazyproperty

from .base import BaseProvider

# Instance attributes
# https://www.alibabacloud.com/help/zh/doc-detail/25506.htm?spm=a2c63.p38356.b99.586.5c501f92MWpqiu


class Provider(BaseProvider):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        info = self.account.attrs.get('service_account_key', {})
        self.project = info.get('project_id', '')
        self.instances_client = InstancesClient.from_service_account_info(info)
        self.regions_client = RegionsClient.from_service_account_info(info)
        self.zones_client = ZonesClient.from_service_account_info(info)
        self.disk_client = DisksClient.from_service_account_info(info)

    def get_zones(self):
        return list(self.zones_client.list(project=self.project))

    @lazyproperty
    def regions_zones_map(self):
        regions_zones_map = defaultdict(set)
        zones = self.get_zones()
        for zone in zones:
            region = zone.region.split('/')[-1]
            regions_zones_map[region].add(zone.name)
        return regions_zones_map

    def get_region_of_zone(self, zone):
        for region, zones in self.regions_zones_map.items():
            if zone in zones:
                return region
        return 'Unknown Region'

    def get_regions(self):
        """
        :return - {region_id: region_name, region_id: region_name}
        """
        # raise error => https://github.com/googleapis/google-api-python-client/issues/1503
        # regions = self.regions_client.list(project=self.project)
        regions = {region: region for region in self.regions_zones_map.keys()}
        return regions

    def preset_instance_properties(self, *args, **kwargs):
        pass

    def _is_valid(self):
        self.get_instances_of_zone(zone='us-central1-a')

    def get_instances_of_region(self, region_id):
        instances = []
        zones = self.regions_zones_map.get(region_id, [])
        for zone in zones:
            zone_instances = self.get_instances_of_zone(zone)
            instances.extend(zone_instances)
        return instances

    def get_instances_of_zone(self, zone):
        return list(self.instances_client.list(project=self.project, zone=zone))

    def get_instance_id(self, instance):
        return str(instance.id)

    def get_instance_name(self, instance):
        return instance.name

    def get_instance_platform(self, instance):
        platform = 'linux'
        for disk in instance.disks:
            if not disk.boot:
                continue
            disk_url = disk.source
            disk_url_list = disk_url.split('/')
            zone_name = disk_url_list[-3]
            disk_name = disk_url_list[-1]
            disk_detail = self.disk_client.get(project=self.project, zone=zone_name, disk=disk_name)
            if 'window' in disk_detail.source_image.lower():
                platform = 'windows'
        return platform

    def get_instance_private_ips(self, instance):
        ips = []
        network_interfaces = instance.network_interfaces
        for network_interface in network_interfaces:
            ips.append(network_interface.network_i_p)
        return ips

    def get_instance_public_ip(self, instance):
        # google 好像只支持外部 ipv6 地址，且对于外部 ipv6 的配置没有返回
        # https://cloud.google.com/compute/docs/ip-addresses/configure-ipv6-address?hl=zh_cn#update-vm-ipv6
        ips = []
        network_interfaces = instance.network_interfaces
        for network_interface in network_interfaces:
            for access_config in network_interface.access_configs:
                ips.append(access_config.nat_i_p)
        ip = ips[0] if ips else ''
        return ip

    def get_instance_region_id(self, instance):
        zone = instance.zone.split('/')[-1]
        region = self.get_region_of_zone(zone)
        return region

    def get_instance_vpc_id(self, instance):
        vpc_name = 'default'
        if len(instance.network_interfaces) > 0:
            vpc_name = instance.network_interfaces[0].network.split('/')[-1]
        return vpc_name
