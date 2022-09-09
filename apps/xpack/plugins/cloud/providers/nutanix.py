# -*- coding: utf-8 -*-
import re
import requests
from django.utils.translation import ugettext_lazy as _

from .base import BaseProvider

# API
# https://www.nutanix.dev/reference/prism_element/v2/api/


class Provider(BaseProvider):
    DISPLAY = _('Nutanix')
    NAME = 'nutanix'

    ip_reg = '^((25[0-5]|2[0-4]\\d|((1\\d{2})|([1-9]?\\d)))\\.){3}(25[0-5]|2[0-4]\\d|((1\\d{2})|([1-9]?\\d)))$'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ak = self.account.attrs.get('access_key_id')
        self.secret = self.account.attrs.get('access_key_secret')
        self.api_endpoint = self.account.attrs.get('api_endpoint')
        self.page_size = 20
        self.image_platform_map = {}
        self.vpcs = []  # 存放当前账户所有的vpcs

    def get_regions(self):
        regions = {
            'default': _('Default'),
        }
        return regions

    def set_current_region(self, region):
        pass

    def _is_valid(self):
        try:
            self.__post_pagination(self.api_endpoint + '/clusters/list')
        except Exception as e:
            raise PermissionError(e)

    def get_instance_by_id(self, instance_id, region):
        server = self.__post_http_request(self.api_endpoint + '/vms/' + instance_id)
        return server, region

    def get_instances_of_region(self, region):
        servers = self.__post_pagination(self.api_endpoint + '/vms/list')
        return list(servers)

    def get_instance_id(self, instance):
        return instance['metadata']['uuid']

    def get_instance_name(self, instance):
        return instance['spec']['name']

    def _preset_instance_properties(self, instance):
        pass

    def get_instance_platform(self, instance):
        instance_id = instance['metadata']['uuid']
        try:
            guest_os_version = instance['status']['resources']['guest_tools']['nutanix_guest_tools']['guest_os_version']
            os_type = guest_os_version.split(':')[0].lower()
            return os_type
        except Exception as e:
            # 没有安装ngt的机器无法拿到系统类型信息，默认为Linux
            print(f'Get platform error with instance {instance_id}: {e}')
            return 'linux'

    def get_instance_private_ips(self, instance):
        nic_list = list(instance['status']['resources']['nic_list'])
        ips = []
        for nic in nic_list:
            if 'ip_endpoint_list' in nic:
                for ip_endpoint in nic['ip_endpoint_list']:
                    ip_address = ip_endpoint['ip']
                    ip_matcher = re.match(self.ip_reg, ip_address)
                    if ip_matcher:
                        ips.append(ip_address)
        return ips

    def get_instance_public_ip(self, instance):
        return None

    @staticmethod
    def set_instance_region_id(instance, region):
        instance['region_id'] = region

    def get_instance_region_id(self, instance):
        return instance['region_id']

    def get_vpcs(self):
        """ 获取当前账户所有的vpcs """
        if len(self.vpcs) == 0:
            self.vpcs = self.__post_pagination(self.api_endpoint + '/subnets/list')
        return self.vpcs

    def get_instance_vpc_id(self, instance):
        vpcs = self.get_vpcs()
        nic_list = list(instance['status']['resources']['nic_list'])
        for nic in nic_list:
            if 'ip_endpoint_list' in nic and 'subnet_reference' in nic:
                for ip_endpoint in nic['ip_endpoint_list']:
                    ip_address = ip_endpoint['ip']
                    ip_matcher = re.match(self.ip_reg, ip_address)
                    if ip_matcher:
                        vpc_id = nic['subnet_reference']['uuid']
                        for vpc in vpcs:
                            if vpc_id == vpc['metadata']['uuid']:
                                return vpc['status']['name']
        print('[DEBUG] vpcs: {}, vpcs_id: {}'.format([vpc['uuid'] for vpc in vpcs], instance))
        return 'default'

    @staticmethod
    def __suppress_security():
        # suppress the security warnings
        requests.packages.urllib3.disable_warnings()

    def __post_pagination(self, url):
        results = []
        page_size = 100
        offset = 0
        params = {"offset": offset, "length": page_size}

        entities = self.__post_http_request(url, params)['entities']
        while len(entities) > 0:
            results.extend(entities)
            offset += page_size
            if len(entities) < page_size:
                break
            params = {"offset": offset, "length": page_size}
            entities = self.__post_http_request(url, params)['entities']
        return results

    def __post_http_request(self, url, json_data):
        self.__suppress_security()
        s = requests.Session()
        s.auth = (self.ak, self.secret)
        s.headers.update({'Content-Type': 'application/json; charset=utf-8'})
        if json_data is None:
            json_data = {}
        result = s.post(url, json=json_data, verify=False)
        return result.json()

