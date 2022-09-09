# -*- coding: utf-8 -*-
#
import abc
from hashlib import md5
import uuid

from common.utils import get_logger
from common.utils.ip import contains_ip
from assets.models import Platform, Asset
from .. import const

logger = get_logger(__file__)


class BaseProvider:
    def __init__(self, account):
        self.account = account
        self.ak = self.account.attrs.get('access_key_id', '')
        self.secret = self.account.attrs.get('access_key_secret', '')
        self.platform_mapping = {
            p.name.lower(): p for p in Platform.objects.all().only('id', 'name', 'base')
        }

    def get_display_name(self):
        return self.account.provider_display

    def build_asset_id(self, instance):
        asset_id = self.get_instance_uuid(instance)
        org_id = str(self.account.org_id)
        if org_id:
            asset_id = asset_id[:18] + org_id[:18]
        return uuid.UUID(asset_id)

    def build_asset_hostname(self, instance, hostname_strategy, asset_ip):
        asset_id = self.build_asset_id(instance)
        instance_name = self.get_instance_name(instance) or 'untitled'
        if hostname_strategy == const.HostnameStrategyChoices.instance_name_partial_ip:
            asset_ip_last_two_bit = '.'.join(asset_ip.split('.')[2:])
            hostname = '{}-{}'.format(instance_name, asset_ip_last_two_bit)
        else:
            hostname = instance_name
        # 如果主机名已存在但与当前资产的主机名不同, 则需要使用新的主机名, 防止创建时资产时主机名重复报错
        # 场景如: AWS实例在释放的过程中, 执行同步任务, 实例能获取到, 实例名称相同(mx-server),
        #        IP获取不到(0.0.0.0), 导致构建的主机名一致(mx-server-0.0), 多个释放的实例主机名重复，
        #        创建/更新资产时报错
        if Asset.objects.exclude(id=asset_id).filter(hostname=hostname).exists():
            instance_id = self.get_instance_id(instance)
            instance_id_last_four_bit = instance_id[-4:]
            hostname = '{}-{}'.format(hostname, instance_id_last_four_bit)
        return hostname

    def build_asset_ip(self, instance, ip_network_segment_group):
        ips = self.get_instance_private_ips(instance)
        matched_ips = [ip for ip in ips if contains_ip(ip, ip_network_segment_group)]
        if len(matched_ips) > 0:
            ip = matched_ips[0]
        elif len(ips) > 0:
            ip = ips[0]
        else:
            ip = '0.0.0.0'
        return ip

    def build_asset_public_ip(self, instance):
        public_ip = self.get_instance_public_ip(instance)
        return public_ip or ''

    def build_asset_platform(self, instance):
        platform_name = self.get_instance_platform(instance)
        if isinstance(platform_name, str):
            platform_name = platform_name.lower()
        if platform_name not in self.platform_mapping:
            platform_name = 'linux'
        platform = self.platform_mapping[platform_name]
        return platform

    def build_asset_nodes_name(self, instance):
        provider_display = self.account.provider_display
        folders_name = self.get_instance_folders_name(instance)
        nodes_name = [provider_display, *folders_name]
        return nodes_name

    def build_asset_domain_id(self, instance):
        vpc_uuid = self.get_instance_vpc_uuid(instance)
        org_id = str(self.account.org_id)
        if org_id:
            domain_id = vpc_uuid[:18] + org_id[:18]
        else:
            domain_id = vpc_uuid
        return uuid.UUID(domain_id)

    def build_asset_domain_name(self, instance):
        vpc_id = self.get_instance_vpc_id(instance)
        domain_name = "{} ({})".format(self.get_display_name(), vpc_id)
        return domain_name

    def get_instance_folders_name(self, instance):
        region_display = self.get_instance_region_display(instance)
        vpc_id = self.get_instance_vpc_id(instance)
        folders_name = [region_display, vpc_id]
        return folders_name

    def get_instance_uuid(self, instance):
        instance_id = self.get_instance_id(instance)
        return str(uuid.UUID(md5(instance_id.encode('utf-8')).hexdigest()))

    def get_instance_vpc_uuid(self, instance):
        vpc_id = self.get_instance_vpc_id(instance)
        return str(uuid.UUID(md5(vpc_id.encode('utf-8')).hexdigest()))

    def get_instance_region_display(self, instance):
        region_id = self.get_instance_region_id(instance)
        regions = self.get_regions()
        region_name = regions.get(region_id)
        return region_name

    def preset_instance_properties(self, instance, properties):
        """ 预设实例不直接包含的属性值，方便后续获取 """
        if isinstance(instance, dict):
            for key, value in properties.items():
                instance[key] = value
        else:
            for key, value in properties.items():
                setattr(instance, key, value)
        self._preset_instance_properties(instance=instance)

    def is_valid(self, return_tuples=False):
        try:
            self._is_valid()
        except Exception as e:
            error = getattr(e, 'msg', str(e))
        else:
            error = ''
        is_valid = not bool(error)
        return (is_valid, error) if return_tuples else is_valid

    @abc.abstractmethod
    def get_regions(self):
        """
        :return - {region_id: region_name, region_id: region_name}
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _is_valid(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _preset_instance_properties(self, instance):
        raise NotImplementedError

    @abc.abstractmethod
    def get_instances_of_region(self, region_id):
        raise NotImplementedError

    @abc.abstractmethod
    def get_instance_id(self, instance):
        raise NotImplementedError

    @abc.abstractmethod
    def get_instance_name(self, instance):
        raise NotImplementedError

    @abc.abstractmethod
    def get_instance_platform(self, instance):
        raise NotImplementedError

    @abc.abstractmethod
    def get_instance_private_ips(self, instance):
        raise NotImplementedError

    @abc.abstractmethod
    def get_instance_public_ip(self, instance):
        raise NotImplementedError

    @abc.abstractmethod
    def get_instance_region_id(self, instance):
        raise NotImplementedError

    @abc.abstractmethod
    def get_instance_vpc_id(self, instance):
        raise NotImplementedError
