#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 腾讯云
import math
import json

from .base import BaseProvider

from tencentcloud.common import credential
from tencentcloud.cvm.v20170312 import cvm_client, models as old_models
from tencentcloud.api.v20201106 import api_client, models

from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.profile.client_profile import ClientProfile

# Regions
# https://cloud.tencent.com/document/product/213/6091
# https://console.cloud.tencent.com/api/explorer?Product=api&Version=2020-11-06&Action=DescribeRegions&SignVersion=

# Instance attributes
# https://cloud.tencent.com/document/api/213/15753


class Provider(BaseProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.credential = credential.Credential(self.ak, self.secret)
        self.page_size = 20

    def _is_valid(self):
        client = cvm_client.CvmClient(self.credential, region=None)
        request = models.DescribeRegionsRequest()
        client.DescribeRegions(request)

    def get_regions(self):
        http_profile = HttpProfile()
        http_profile.endpoint = "api.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = api_client.ApiClient(self.credential, "", client_profile)
        request = models.DescribeRegionsRequest()
        params = {'Product': 'cvm'}
        request.from_json_string(json.dumps(params))
        response = client.DescribeRegions(request)
        regions = {region.Region: region.RegionName for region in response.RegionSet}
        return regions

    def get_instances_of_region(self, region_id):
        instances = []
        client = cvm_client.CvmClient(self.credential, region_id)
        pages = self.get_total_pages(client)
        request = old_models.DescribeInstancesRequest()
        request.Limit = self.page_size
        for page in range(pages):
            request.Offset = page * self.page_size
            result = client.DescribeInstances(request)
            instances.extend(result.InstanceSet)
        return instances

    def get_total_pages(self, client):
        request = old_models.DescribeInstancesRequest()
        request.Limit = 1
        request.Offset = 0
        result = client.DescribeInstances(request)
        total_pages = int(math.ceil(result.TotalCount / self.page_size))
        return total_pages

    def _preset_instance_properties(self, instance):
        # private ip
        private_ips = instance.PrivateIpAddresses
        private_ips = private_ips if isinstance(private_ips, list) else []
        # public ip
        public_ips = instance.PublicIpAddresses
        public_ip = public_ips[0] if isinstance(public_ips, list) and len(public_ips) > 0 else None
        # set
        setattr(instance, 'private_ips', private_ips)
        setattr(instance, 'public_ip', public_ip)

    def get_instance_id(self, instance):
        return instance.InstanceId

    def get_instance_name(self, instance):
        return instance.InstanceName

    def get_instance_platform(self, instance):
        return instance.OsName

    def get_instance_private_ips(self, instance):
        return getattr(instance, 'private_ips')

    def get_instance_public_ip(self, instance):
        return getattr(instance, 'public_ip')

    def get_instance_region_id(self, instance):
        return getattr(instance, 'region_id')

    def get_instance_vpc_id(self, instance):
        return instance.VirtualPrivateCloud.VpcId
