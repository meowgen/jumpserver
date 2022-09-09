from django.utils.translation import ugettext_lazy as _
from baidubce.auth.bce_credentials import BceCredentials
from baidubce.bce_client_configuration import BceClientConfiguration
from baidubce.services.bcc import bcc_client

from .base import BaseProvider


class Provider(BaseProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client = None
        self._image_map = None
        self.region_id = 'bj'

    def _is_valid(self):
        self.client.list_zones()

    @property
    def client(self):
        if self._client is None:
            self._client = self.get_client()
        return self._client

    @property
    def image_map(self):
        if self._image_map is None:
            self._image_map = self.get_image_map()
        return self._image_map

    def get_client(self, region='bj'):
        host = self.get_host(region)
        config = BceClientConfiguration(credentials=BceCredentials(self.ak, self.secret), endpoint=host)
        return bcc_client.BccClient(config)

    def get_image_map(self):
        images = self.client.list_images().images
        return {image.id: image.os_type for image in images}

    def set_region(self, region):
        self.region_id = region
        self._client = self.get_client(region)

    @staticmethod
    def get_host(region):
        return 'http://bcc.{}.baidubce.com'.format(region)

    def get_os_type(self, image_id):
        return self.image_map.get(image_id, 'linux')

    def get_regions(self):
        # TODO: There is no api
        regions = {
            'bj': _('CN North-Beijing'),
            'gz': _('CN South-Guangzhou'),
            'su': _('CN East-Suzhou'),
            'hkg': _('CN-Hong Kong'),
            'fwh': _('CN Center-Wuhan'),
            'bd': _('CN North-Baoding'),
            'fsh': _('CN East-Shanghai'),
            'sin': _('AP-Singapore'),
        }
        return regions

    def get_instances_of_region(self, region_id):
        self.set_region(region_id)
        response = self.client.list_instances()
        instances = getattr(response, 'instances', [])
        return instances

    def _preset_instance_properties(self, instance):
        # private ip
        private_ips = [getattr(i, 'private_ip') for i in instance.nic_info.ips]
        # set
        setattr(instance, 'private_ips', private_ips)
        setattr(instance, 'region_id', self.region_id)

    def get_instance_id(self, instance):
        return instance.id

    def get_instance_name(self, instance):
        return instance.name

    def get_instance_platform(self, instance):
        return self.image_map.get(instance.image_id)

    def get_instance_private_ips(self, instance):
        return getattr(instance, 'private_ips')

    def get_instance_public_ip(self, instance):
        return instance.public_ip

    def get_instance_region_id(self, instance):
        return instance.region_id

    def get_instance_vpc_id(self, instance):
        return instance.vpc_id

