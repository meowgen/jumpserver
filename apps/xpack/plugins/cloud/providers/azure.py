# -*- coding: utf-8 -*-
#


from .base import BaseProvider

import adal
from msrestazure.azure_active_directory import AdalAuthentication
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.subscription import SubscriptionClient
from azure.identity import ClientSecretCredential
from msrestazure.azure_cloud import AZURE_CHINA_CLOUD


class Provider(BaseProvider):
    authentication_endpoint = 'https://login.chinacloudapi.cn/'
    azure_endpoint = 'https://management.chinacloudapi.cn/'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client_id = self.account.attrs.get('client_id', '')
        self.client_secret = self.account.attrs.get('client_secret', '')
        self.tenant_id = self.account.attrs.get('tenant_id', '')
        self.subscription_id = self.account.attrs.get('subscription_id', '')

        context = adal.AuthenticationContext(self.authentication_endpoint+self.tenant_id)
        credentials = AdalAuthentication(
            context.acquire_token_with_client_credentials,
            self.azure_endpoint, self.client_id, self.client_secret
        )
        self.compute_client = ComputeManagementClient(
            credentials, self.subscription_id, base_url=self.azure_endpoint
        )
        self.network_client = NetworkManagementClient(
            credentials, self.subscription_id, base_url=self.azure_endpoint
        )

        _credentials = ClientSecretCredential(self.tenant_id, self.client_id, self.client_secret)
        self.subscription_client = SubscriptionClient(_credentials, self.azure_endpoint)

    def _is_valid(self):
        list(self.compute_client.virtual_machines.list_all())

    def get_regions(self):
        # TODO: Get regions by api
        regions = {
            'chinanorth': '中国北部',
            'chinanorth2': '中国北部 2',
            'chinaeast': '中国东部',
            'chinaeast2': '中国东部 2',
        }
        return regions

    def get_instances_of_region(self, region_id):
        instances = list(self.compute_client.virtual_machines.list_by_location(location=region_id))
        return instances

    def _preset_instance_properties(self, instance):
        network_interface = instance.network_profile.network_interfaces[0]
        network_interface_name = network_interface.id.split('/')[-1]
        resource_group_name = network_interface.id.split('/')[4]
        network_interface = self.network_client.network_interfaces.get(
            resource_group_name, network_interface_name
        )
        ip_configuration = network_interface.ip_configurations[0]
        # private ip
        private_ips = [ip_configuration.private_ip_address]
        # public ip
        if ip_configuration.public_ip_address is None:
            public_ip = ''
        else:
            public_ip_name = ip_configuration.public_ip_address.id.split('/')[-1]
            public_ip_address = self.network_client.public_ip_addresses.get(
                resource_group_name, public_ip_name
            )
            public_ip = public_ip_address.ip_address
        # virtual network name
        if ip_configuration.subnet is None:
            virtual_network_name = 'default'
        else:
            virtual_network_name = ip_configuration.subnet.id.split('/')[8]
        # set
        setattr(instance, 'vpc_id', virtual_network_name)
        setattr(instance, 'private_ips', private_ips)
        setattr(instance, 'public_ip', public_ip)

    def get_instance_id(self, instance):
        return instance.vm_id

    def get_instance_name(self, instance):
        return instance.name

    def get_instance_platform(self, instance):
        # TODO: maybe raise error
        return instance.storage_profile.os_disk.os_type.name

    def get_instance_private_ips(self, instance):
        return getattr(instance, 'private_ips')

    def get_instance_public_ip(self, instance):
        return getattr(instance, 'public_ip')

    def get_instance_region_id(self, instance):
        return instance.location

    def get_instance_vpc_id(self, instance):
        return getattr(instance, 'vpc_id')
