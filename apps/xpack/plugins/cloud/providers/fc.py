# -*- coding: utf-8 -*-
import hashlib

import requests

from django.utils.translation import ugettext_lazy as _

from .base import BaseProvider


class Client(object):
    def __init__(self, account):
        self._host = account.get('api_endpoint')
        self.username = account.get('username')
        self._password = account.get('password')
        self._token = None
        self.site = None
        self.limit = 40

    @property
    def host(self):
        if str(self._host).endswith('/'):
            self._host = self._host[:-1]
        return self._host

    @property
    def password(self):
        hash_obj = hashlib.sha256()
        hash_obj.update(bytes(self._password, encoding='utf-8'))
        return hash_obj.hexdigest()

    @property
    def token(self):
        if self._token is None:
            self._token = self.get_token()
        return self._token

    def get_token(self):
        session_url = '%s/service/session' % self.host
        headers = {
            'X-Auth-User': self.username,
            'X-Auth-Key': self.password,
            'X-Auth-UserType': '0',
        }
        resp = requests.post(session_url, headers=headers, verify=False)
        token = resp.headers.get('X-Auth-Token')
        if token is None:
            raise Exception(_('Authentication failed'))
        return token

    def send(self, url, method='get', body=None):
        headers = {
            'X-Auth-Token': self.token
        }
        if body is None:
            body = {}
        url = '%s/service%s' % (self.host, url)
        action = getattr(requests, method)
        resp = action(url, headers=headers, json=body, verify=False)
        return resp.json()

    def set_region_id(self, region_id):
        self.site = region_id

    def describe_regions(self):
        resp = self.send('/sites')
        sites = {}
        try:
            sites_data = resp.get('sites')
            for s in sites_data:
                value = s['uri'].rsplit('/', 1)[1]
                sites[value] = s['name']
        except Exception:
            pass
        return sites

    def describe_instances(self):
        instances = []
        total, offset = 1, 0
        while offset < total:
            uri = '/sites/%s/vms?detail=2&offset=%s&limit=%s' % (self.site, offset, self.limit)
            resp = self.send(uri)
            total = resp.get('total', 1)
            offset += self.limit
            vms = resp.get('vms', [])
            instances.extend(vms)
        return instances


class Provider(BaseProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = Client(self.account.attrs)

    def _is_valid(self):
        self.client.get_token()

    def get_regions(self):
        return self.client.describe_regions()

    def get_instances_of_region(self, region_id):
        self.client.set_region_id(region_id)
        instances = self.client.describe_instances()
        return instances

    def _preset_instance_properties(self, instance):
        ips = instance['vmConfig']['nics'][0]['ipList'].split(';')
        instance['private_ips'] = ips
        instance['vpc_id'] = ''
        instance['public_ip'] = ''

    def get_instance_id(self, instance):
        return instance.get('uuid')

    def get_instance_name(self, instance):
        return instance.get('name')

    def get_instance_platform(self, instance):
        return instance.get('osOptions', {}).get('osType')

    def get_instance_private_ips(self, instance):
        return instance.get('private_ips')

    def get_instance_public_ip(self, instance):
        return instance.get('public_ip')

    def get_instance_region_id(self, instance):
        return instance.get('region_id')

    def get_instance_vpc_id(self, instance):
        return instance.get('vpc_id')
