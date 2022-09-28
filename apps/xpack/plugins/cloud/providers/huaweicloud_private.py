# -*- coding: utf-8 -*-
import requests

from datetime import datetime, timedelta
from urllib.parse import urlparse

from .base import BaseProvider


class Client:
    def __init__(self, account_attr):
        for name, value in account_attr.items():
            setattr(self, name, value)
        url_parse_result = urlparse(self.api_endpoint)
        self.iam_api_endpoint = url_parse_result.scheme + '://iam-apigateway-proxy.' + url_parse_result.netloc
        self.sc_api_endpoint = url_parse_result.scheme + '://sc.' + url_parse_result.netloc
        self.base_oc_api_endpoint = url_parse_result.scheme + '://oc.{}.' + url_parse_result.netloc
        self.sc_token_msg = {}
        self.oc_token_msg = {}
        self.region_id = ''
        self.limit = 40

    @property
    def oc_api_endpoint(self):
        return self.base_oc_api_endpoint.format(self.region_id)

    def get_oc_token(self):
        data = {
            "grantType": "password",
            "userName": self.oc_username,
            "value": self.oc_password
        }
        response = requests.put(
            self.oc_api_endpoint + '/rest/plat/smapp/v1/oauth/token',
            json=data, verify=False)
        if oc_token := response.json().get('accessSession'):
            self.oc_token_msg['token'] = oc_token
            self.oc_token_msg['created_date'] = datetime.now()
        else:
            raise Exception('OC Authentication failed: {}'.format(response.json()))

    def get_sc_token(self):
        data = {
            "auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "domain": {
                                "name": self.domain_name
                            },
                            "name": self.sc_username,
                            "password": self.sc_password
                        }
                    }
                },
                "scope": {
                    "domain": {
                        "name": self.domain_name
                    }
                }
            }
        }
        response = requests.post(
            self.iam_api_endpoint + '/v3/auth/tokens',
            json=data, verify=False)
        if sc_token := response.headers.get('X-Subject-Token'):
            self.sc_token_msg['token'] = sc_token
            self.sc_token_msg['created_date'] = datetime.now()
        else:
            raise Exception('SC Authentication failed: {}'.format(response.json()))

    @property
    def sc_token(self):
        if not self.sc_token_msg.get('token'):
            self.get_sc_token()
        elif self.sc_token_msg.get('token') and \
                datetime.now() > self.sc_token_msg['created_date'] + timedelta(hours=23):
            self.get_sc_token()
        return self.sc_token_msg['token']

    @property
    def oc_token(self):
        if not self.oc_token_msg.get('token'):
            self.get_oc_token()
        elif self.oc_token_msg.get('token') and \
                datetime.now() > self.oc_token_msg['created_date'] + timedelta(minutes=29):
            self.get_oc_token()
        return self.oc_token_msg['token']

    def set_region_id(self, region_id):
        self.region_id = region_id

    def describe_regions(self):
        headers = {'x-auth-token': self.sc_token}
        response = requests.get(
            self.sc_api_endpoint + '/rest/serviceaccess/v3.0/regions',
            headers=headers, verify=False
        )
        regions = response.json().get('records', [])
        return regions

    def describe_instances(self):
        instances = []
        headers = {'x-auth-token': self.oc_token}
        current_page = 0
        while True:
            params = {'limit': self.limit, 'offset': self.limit * current_page}
            response = requests.get(
                self.oc_api_endpoint + '/rest/tenant-resource/v1/tenant/resources/CLOUD_VM',
                headers=headers, params=params, verify=False
            )
            response_json = response.json()
            current_page = response_json.get('currentPage', 1)
            total_page = response_json.get('totalPageNo', 1)
            per_page_instances = [
                instance for instance in response_json.get('objList')
                if instance.get('privateIps', '')
            ]
            instances.extend(per_page_instances)
            if current_page >= total_page:
                break
        return instances


class Provider(BaseProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = Client(self.account.attrs)

    def _is_valid(self):
        region = self.get_regions().popitem()
        self.client.set_region_id(region[0])
        self.client.get_oc_token()

    def get_regions(self):
        regions = self.client.describe_regions()
        regions = {region['id']: region['name'] for region in regions}
        return regions

    def get_instances_of_region(self, region_id):
        self.client.set_region_id(region_id)
        instances = self.client.describe_instances()
        return instances

    def _preset_instance_properties(self, instance):
        if ips := instance.get('privateIps', ''):
            ips = ips.strip('@').split('@')
        else:
            ips = []
        instance['private_ips'] = ips
        instance['vpc_id'] = ''
        instance['public_ip'] = ''

    def get_instance_id(self, instance):
        return instance.get('id')

    def get_instance_name(self, instance):
        return instance.get('name')

    def get_instance_platform(self, instance):
        return instance.get('osType', 'linux')

    def get_instance_private_ips(self, instance):
        return instance.get('private_ips')

    def get_instance_public_ip(self, instance):
        return instance.get('public_ip')

    def get_instance_region_id(self, instance):
        return instance.get('region_id')

    def get_instance_vpc_id(self, instance):
        return instance.get('vpc_id')
