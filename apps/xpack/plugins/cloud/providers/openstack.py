# -*- coding: utf-8 -*-
from keystoneauth1 import session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client
from novaclient.client import Client as NovaClient

from .base import BaseProvider


class Client:
    def __init__(self, **kwargs):
        self._token = None
        self._nova_client = None
        self._image_mapping = None
        self.auth_params = kwargs
        self.conn = self.get_client(**kwargs)

    @property
    def token(self):
        if self._token is None:
            self._token = self.conn.session.get_token()
        return self._token

    @property
    def _nova(self):
        if self._nova_client is None:
            self._nova_client = self.get_nova_client(
                token=self.token, **self.auth_params
            )
        return self._nova_client

    @property
    def image_mapping(self):
        if self._image_mapping is None:
            self._image_mapping = {
                image.id: image.name
                for image in self._nova_client.glance.list()
            }
        return self._image_mapping

    @staticmethod
    def get_client(**kwargs):
        auth = v3.Password(**kwargs)
        keystone_session = session.Session(auth=auth)
        return client.Client(session=keystone_session)

    def get_nova_client(self, **kwargs):
        auth_url = kwargs['auth_url']
        project_id = kwargs['project_id']
        user_domain_name = kwargs['user_domain_name']
        return NovaClient(
            version='2', auth_url=auth_url, project_id=project_id,
            auth_token=self.token, user_domain_name=user_domain_name
        )

    def set_region_id(self, region_id):
        self._nova_client = self.get_nova_client(
            project_id=region_id, **self.auth_params
        )

    def get_projects(self):
        user_id = self.conn.session.get_user_id()
        return self.conn.projects.list(user=user_id)

    def get_instances(self):
        return self._nova.servers.list(limit=-1)


class Provider(BaseProvider):
    def __init__(self, **kwargs):
        """
        :param self.account.attr include:
            auth_url
            user_domain_name
            username
            password
        """
        super().__init__(**kwargs)
        self.client = Client(**self.account.attrs)

    def _is_valid(self):
        self.client.get_projects()

    def get_regions(self):
        projects = self.client.get_projects()
        return {project.id: project.name for project in projects}

    def get_instances_of_region(self, region_id):
        self.client.set_region_id(region_id)
        return self.client.get_instances()

    def _preset_instance_properties(self, instance):
        # platform
        metadata = getattr(instance, 'metadata')
        platform = metadata.get('os_type') if metadata else ''
        if not platform:
            image = getattr(instance, 'image')
            image_id = image.get('id', '') if image else ''
            image_name = self.client.image_mapping.get(image_id, 'linux')
            platform = 'windows' if 'win' in image_name else 'linux'
        # private_ips
        networks = list(getattr(instance, 'networks', {}).values())
        private_ips = networks[0] if len(networks) > 0 else []
        # vpc_id
        vpc_id = getattr(instance, 'OS-EXT-AZ:availability_zone', '')

        setattr(instance, 'private_ips', private_ips)
        setattr(instance, 'platform', platform)
        setattr(instance, 'vpc_id', vpc_id)
        setattr(instance, 'public_ip', '')

    def get_instance_id(self, instance):
        return getattr(instance, 'id')

    def get_instance_name(self, instance):
        return getattr(instance, 'name')

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
