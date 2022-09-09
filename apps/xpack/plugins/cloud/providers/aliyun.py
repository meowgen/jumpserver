# -*- coding: utf-8 -*-
#

import json
import math
from .base import BaseProvider

from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest, DescribeRegionsRequest

# Instance attributes
# https://www.alibabacloud.com/help/zh/doc-detail/25506.htm?spm=a2c63.p38356.b99.586.5c501f92MWpqiu


class Provider(BaseProvider):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = AcsClient(ak=self.ak, secret=self.secret)
        self.page_size = 10

    def _is_valid(self):
        request = DescribeInstancesRequest.DescribeInstancesRequest()
        self.client.set_region_id('cn-qingdao')
        self.client.do_action_with_exception(request)

    def get_regions(self):
        request = DescribeRegionsRequest.DescribeRegionsRequest()
        # zh-CN / en-US
        # request.set_AcceptLanguage('en-US')
        request.set_accept_format('json')
        response = self.client.do_action_with_exception(request)
        response = json.loads(response)
        regions = response.get('Regions', {}).get('Region', [])
        regions = {region['RegionId']: region['LocalName'] for region in regions}
        return regions

    def get_instances_of_region(self, region_id):
        instances = []
        self.client.set_region_id(region_id)
        pages = self.get_total_pages()
        for page in range(1, pages+1):
            instances_page = self.get_instances_of_page(page)
            instances.extend(instances_page)
        return instances

    def get_instances_of_page(self, page):
        response = self.get_response_of_page(page)
        if not response:
            return []
        instances = response.get('Instances').get('Instance')
        return instances

    def get_total_pages(self):
        response = self.get_response_of_page(page=1)
        if not response:
            return 0
        total_count = response.get('TotalCount')
        total_pages = int(math.ceil(total_count/self.page_size))
        return total_pages

    def get_response_of_page(self, page):
        request = DescribeInstancesRequest.DescribeInstancesRequest()
        request.set_PageNumber(page)
        request.set_PageSize(self.page_size)
        try:
            response = self.client.do_action_with_exception(request)
            response = json.loads(response)
            return response
        except Exception as e:
            print('Error get response of page: {}'.format(e))
            return None

    def _preset_instance_properties(self, instance):
        network_type = instance.get('InstanceNetworkType', '')
        if network_type == 'vpc':
            # vpc
            private_ips = instance.get('VpcAttributes').get('PrivateIpAddress').get('IpAddress')
            vpc_id = instance.get('VpcAttributes').get('VpcId')
        else:
            # classic
            private_ips = instance.get('InnerIpAddress').get('IpAddress')
            vpc_id = network_type
        # private ip
        private_ips = private_ips if isinstance(private_ips, list) else []
        # public ip
        public_ips = instance.get('PublicIpAddress').get('IpAddress')
        public_ip = public_ips[0] if len(public_ips) > 0 else None
        # set
        instance['vpc_id'] = vpc_id
        instance['private_ips'] = private_ips
        instance['public_ip'] = public_ip

    def get_instance_uuid(self, instance):
        return instance.get('SerialNumber')

    def get_instance_id(self, instance):
        return instance.get('InstanceId')

    def get_instance_name(self, instance):
        return instance.get('InstanceName')

    def get_instance_platform(self, instance):
        return instance.get('OSType', 'linux')

    def get_instance_private_ips(self, instance):
        return instance.get('private_ips')

    def get_instance_public_ip(self, instance):
        return instance.get('public_ip')

    def get_instance_region_id(self, instance):
        return instance.get('RegionId')

    def get_instance_vpc_id(self, instance):
        return instance.get('vpc_id')

