# -*- coding: utf-8 -*-
import math
import ssl

from urllib.parse import urlparse

from qingcloud.iaas.connection import APIConnection

from .base import BaseProvider


ssl._create_default_https_context = ssl._create_unverified_context


class Client:
    def __init__(self, ak, secret, api_endpoint):
        self.ak = ak
        self.secret = secret
        self.api_endpoint = api_endpoint
        self.conn = self.get_conn()

    def get_conn_option(self):
        url_struct = urlparse(self.api_endpoint)
        path = url_struct.netloc if url_struct.scheme else url_struct.path
        scheme = url_struct.scheme if url_struct.scheme else 'https'
        if path.find(':') != -1:
            host, port = path.rsplit(':')
        else:
            host = path
            port = 80 if scheme == 'http' else 443
        return scheme, host, port

    def get_conn(self, region_id=None):
        options = {
            'qy_access_key_id': self.ak,
            'qy_secret_access_key': self.secret,
            'zone': region_id
        }
        protocol, host, port = self.get_conn_option()
        options.update({
            'host': host, 'port': port, 'protocol': protocol
        })
        return APIConnection(**options)

    def set_region_id(self, region_id):
        self.conn = self.get_conn(region_id)


class Provider(BaseProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_endpoint = self.account.attrs.get('api_endpoint')
        self.page_size = 40
        self.client = Client(self.ak, self.secret, self.api_endpoint)

    def _is_valid(self):
        response = self.client.conn.describe_zones()
        if response.get('ret_code') != 0:
            raise Exception(response.get('message', 'Authentication failed'))

    def get_regions(self):
        response = self.client.conn.describe_zones()
        regions = response.get('zone_set', [])
        regions = {region['zone_id']: region['zone_id'] for region in regions}
        return regions

    def get_instances_of_page(self, page):
        response = self.get_response_of_page(page)
        if not response:
            return []
        instances = response.get('instance_set', [])
        return instances

    def get_total_pages(self):
        response = self.client.conn.describe_instances(limit=self.page_size, status=['running'])
        if not response:
            return 0
        total_count = response.get('total_count', 0)
        total_pages = int(math.ceil(total_count/self.page_size))
        return total_pages

    def get_response_of_page(self, page):
        try:
            response = self.client.conn.describe_instances(
                offset=(page - 1) * self.page_size, limit=self.page_size, status=['running']
            )
            return response
        except Exception as e:
            print('Error get response of page: {}'.format(e))
            return None

    def get_instances_of_region(self, region_id):
        instances = []
        self.client.set_region_id(region_id)
        pages = self.get_total_pages()
        for page in range(1, pages + 1):
            instances_page = self.get_instances_of_page(page)
            instances.extend(instances_page)
        return instances

    def _preset_instance_properties(self, instance):
        private_ips = []
        if vxnets := instance.get('vxnets'):
            for vxnet in vxnets:
                ip = vxnet.get('private_ip')
                if ip:
                    private_ips.append(ip)
                vpc_id = vxnet.get('vxnet_id', '')
                instance.setdefault('vpc_id', vpc_id)

        instance.setdefault('vpc_id', '')
        instance.setdefault('private_ips', private_ips)
        instance['public_ip'] = instance.get('eip').get('eip_addr') if instance.get('eip') else ''

    def get_instance_id(self, instance):
        return instance.get('instance_id')

    def get_instance_name(self, instance):
        return instance.get('instance_name')

    def get_instance_platform(self, instance):
        return instance['image'].get('platform', 'linux')

    def get_instance_private_ips(self, instance):
        return instance.get('private_ips')

    def get_instance_public_ip(self, instance):
        return instance.get('public_ip')

    def get_instance_region_id(self, instance):
        return instance.get('region_id')

    def get_instance_vpc_id(self, instance):
        return instance.get('vpc_id')
