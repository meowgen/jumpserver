import hashlib
import hmac
import requests
import time
import uuid
import math

from datetime import datetime

from django.utils.translation import ugettext_lazy as _

from common.exceptions import JMSException
from .base import BaseProvider


JDCLOUD3_ALGORITHM = 'JDCLOUD3-HMAC-SHA256'


class JDCloudClient:
    def __init__(self, ak, secret):
        self.version = 'v1'
        self.ak = ak
        self.secret = secret
        self.host = 'https://vm.jdcloud-api.com'
        self.region = 'cn-north-1'
        self.security_token = ''
        self.image_mapping = {}

    @staticmethod
    def __sign(key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def __get_signature_key(self, key, date_stamp, region_name, service_name):
        k_date = self.__sign(('JDCLOUD3' + key).encode('utf-8'), date_stamp)
        k_region = self.__sign(k_date, region_name)
        k_service = self.__sign(k_region, service_name)
        k_signing = self.__sign(k_service, 'jdcloud3_request')
        return k_signing

    @staticmethod
    def __sha256_hash(val):
        return hashlib.sha256(val.encode('utf-8')).hexdigest()

    def __build_canonical_headers(self, headers):
        headers.update({'host': self.host.rsplit('/', 1)[1]})
        canonical_headers, signed_headers = '', ''
        for key, value in headers.items():
            canonical_headers += '%s:%s\n' % (key, value)
            signed_headers += '%s;' % key
        return canonical_headers, signed_headers[:-1]

    def _make_headers(self, method, url, query_string, data):
        headers = {'content-type': 'application/json'}
        now = datetime.utcfromtimestamp(time.time())
        nonce = str(uuid.uuid4())
        jdcloud_date = now.strftime('%Y%m%dT%H%M%SZ')
        date_str = jdcloud_date[:8]
        canonical_headers, signed_headers = self.__build_canonical_headers(headers)
        payload_hash = self.__sha256_hash(data)
        canonical_request = '%s\n%s\n%s\n%s\n%s\n%s' % (
            method, url, query_string, canonical_headers, signed_headers, payload_hash
        )
        credential_scope = '%s/%s/vm/jdcloud3_request' % (date_str, self.region)
        string_to_sign = '%s\n%s\n%s\n%s' % (
            JDCLOUD3_ALGORITHM, jdcloud_date, credential_scope,
            self.__sha256_hash(canonical_request)
        )

        signing_key = self.__get_signature_key(self.secret, date_str, self.region, 'vm')
        encoded = string_to_sign.encode('utf-8')
        signature = hmac.new(signing_key, encoded, hashlib.sha256).hexdigest()

        authorization_header = '%s Credential=%s/%s, SignedHeaders=%s, Signature=%s' % (
            JDCLOUD3_ALGORITHM, self.ak, credential_scope, signed_headers, signature
        )

        new_headers = {
            'x-jdcloud-algorithm': JDCLOUD3_ALGORITHM,
            'x-jdcloud-date': jdcloud_date,
            'x-jdcloud-nonce': nonce,
            'Authorization': authorization_header,
            'x-jdcloud-content-sha256': payload_hash,
        }
        headers.update(new_headers)

        if self.security_token:
            headers.update({'x-jdcloud-security-token': self.security_token})
        return headers

    def _send(self, method, url, query_string='', data=''):
        headers = self._make_headers(method, url, query_string, data)
        url = '%s%s?%s' % (self.host, url, query_string)
        resp = requests.request(method, url, data=data, headers=headers)
        if resp.status_code >= 400:
            raise JMSException(resp.text, resp.status_code)
        return resp.json()

    def update_image_mapping(self):
        image_type = ['public', 'private', 'thirdparty', 'shared']
        for t in image_type:
            # 初始化 total >= size 可变相实现 do...while
            page, size, total = 1, 100, 100
            while int(math.ceil(total/size)) >= page:
                result = self.describe_images(page=page, size=size, image_source=t)
                self.image_mapping.update(result['images'])
                page += 1
                total = result['total']

    def set_region(self, region_id):
        self.region = region_id
        # 更新镜像映射
        self.update_image_mapping()

    def describe_instances(self, page=1, size=1):
        url = '/{version}/regions/{region}/instances'.format(version=self.version, region=self.region)
        query_string = 'pageNumber=%s&pageSize=%s' % (page, size)
        resp = self._send('GET', url, query_string)
        instances_info = {
            'instances': resp['result']['instances'] if resp['result']['instances'] else [],
            'total': resp['result']['totalCount']
        }
        return instances_info

    @staticmethod
    def describe_regions():
        return {
            'cn-north-1': _('CN North-Beijing'),
            'cn-east-1': _('CN East-Suqian'),
            'cn-east-2': _('CN East-Shanghai'),
            'cn-south-1': _('CN South-Guangzhou')
        }

    def describe_images(self, page=1, size=10, image_source='public'):
        url = '/{version}/regions/{region}/images'.format(version=self.version, region=self.region)
        query_string = 'imageSource=%s&pageNumber=%s&pageSize=%s' % (image_source, page, size)
        resp = self._send('GET', url, query_string)
        raw_images = resp['result']['images'] or []
        image_map = {i.get('imageId'): i.get('osType') for i in raw_images}
        images_info = {
            'images': image_map, 'total': resp['result']['totalCount']
        }
        return images_info


class Provider(BaseProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = JDCloudClient(self.ak, self.secret)
        self.page_size = 20

    def _is_valid(self):
        self.client.describe_instances(page=1, size=1)

    def get_regions(self):
        return self.client.describe_regions()

    def get_instances_of_region(self, region_id):
        instances = []
        self.client.set_region(region_id)
        pages = self.get_total_pages()
        for page in range(1, pages + 1):
            result = self.client.describe_instances(page=page, size=self.page_size)
            instances.extend(result['instances'])
        return instances

    def get_total_pages(self):
        instance_info = self.client.describe_instances(page=1, size=1)
        return int(math.ceil(instance_info['total'] / self.page_size))

    def _preset_instance_properties(self, instance):
        # platform
        image_id = instance['imageId']
        platform = self.client.image_mapping.get(image_id)
        # private ip
        private_ips = []
        network = instance['primaryNetworkInterface']['networkInterface']
        primary_ip = network['primaryIp']
        private_ips.append(primary_ip['privateIpAddress'])
        for secondary_ip in network.get('secondaryIps', []):
            if secondary_ip.get('privateIpAddress'):
                private_ips.append(secondary_ip.get('privateIpAddress'))
        # public ip
        public_ip = primary_ip.get('elasticIpAddress')
        # set
        instance['private_ips'] = private_ips
        instance['public_ip'] = public_ip
        instance['platform'] = platform

    def get_instance_id(self, instance):
        return instance.get('instanceId')

    def get_instance_name(self, instance):
        return instance.get('instanceName')

    def get_instance_platform(self, instance):
        return instance.get('platform')

    def get_instance_private_ips(self, instance):
        return instance.get('private_ips')

    def get_instance_public_ip(self, instance):
        return instance.get('public_ip')

    def get_instance_region_id(self, instance):
        return instance.get('region_id')

    def get_instance_vpc_id(self, instance):
        return instance.get('vpcId')
