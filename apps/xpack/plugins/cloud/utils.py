# -*- coding: utf-8 -*-
#
import json

from django.db import transaction
from django.utils import translation
from django.utils.translation import gettext as _

from termcolor import colored
from common.utils import get_logger, get_object_or_none
from common.utils.ip import contains_ip
from assets.models import Asset, ProtocolsMixin, Domain, Node
from . import const

logger = get_logger(__name__)


class ColoredPrinter(object):
    _red = 'red'
    _green = 'green'

    @staticmethod
    def polish(text, color):
        return colored(text=text, color=color)

    @staticmethod
    def _print(text):
        print(text)

    def red(self, text):
        self._print(self.polish(text=text, color=self._red))

    def green(self, text):
        self._print(self.polish(text=text, color=self._green))


colored_printer = ColoredPrinter()


class SyncTaskManager:
    def __init__(self, execution):
        self.execution = execution
        self.task = execution.task
        self.account = execution.task.account
        self.provider = execution.task.account.provider_instance
        # - -
        self.cloud_instance_ids = []
        # 新增、 已同步、 未同步、 已释放
        self.result = {'new': [], 'sync': [], 'unsync': [], 'released': []}

    def run(self):
        print("任务执行开始: {}\n".format(self.task))
        print("#"*50)

        self.account.check_update_validity()
        if self.account.validity:
            colored_printer.green('账号有效.')
            try:
                self.sync()
                _reason = '-'
                _status = const.ExecutionStatusChoices.succeed
            except Exception as e:
                logger.error(e, exc_info=True)
                _status = const.ExecutionStatusChoices.failed
                _reason = str(e)
        else:
            colored_printer.red('账号无效.')
            _status = const.ExecutionStatusChoices.failed
            _reason = _('Account unavailable')

        # update execution
        self.execution.status = _status
        self.execution.reason = _reason[:100]
        self.execution.result = self.result
        self.execution.save()

        # update task
        self.task.date_last_sync = self.execution.date_sync
        self.task.save()

        # show summary
        print("#"*50)
        print("查看任务详细信息路径:\n")
        print("XPack -> 云管中心 -> 任务列表 -> 任务详情(点击任务名称) -> 查看同步历史列表/实例列表\n")
        print('\n总结: \n')
        msg = "新增: {} 已同步: {} 未同步: {} 已释放: {}\n".format(
            len(self.result['new']),
            len(self.result['sync']),
            len(self.result['unsync']),
            len(self.result['released'])
        )
        colored_printer.green(msg)
        print("任务执行结束!\n")

    def sync(self):
        region_ids = self.task.regions
        print("同步地域列表: {}\n".format(region_ids))
        for region_id in region_ids:
            print("\n{}".format("="*50))
            print("地域: {}".format(region_id))
            self.sync_instances_of_region(region_id=region_id)

        released_instances = self._get_released_instances()
        released_instances.update(status=const.InstanceStatusChoices.released)
        result = [{'id': i.instance_id, 'region': i.region} for i in released_instances]
        self.result['released'].extend(result)

    def _get_released_instances(self):
        from .models import SyncInstanceDetail
        instances_saved = SyncInstanceDetail.objects.filter(task=self.task)
        instance_ids_saved = instances_saved.values_list('instance_id', flat=True)
        instance_ids_absent = set(instance_ids_saved) - set(self.cloud_instance_ids)
        instances_absent = instances_saved.filter(instance_id__in=instance_ids_absent)
        return instances_absent

    def sync_instances_of_region(self, region_id):
        try:
            instances = self.provider.get_instances_of_region(region_id)
        except Exception as e:
            error = 'Get instances of region error, region: {}, error: {}'.format(region_id, str(e))
            colored_printer.red(error)
            logger.error(error, exc_info=True)
            instances = []
        for instance in instances:
            # 提前设置一些实例的前置属性
            properties = {'region_id': region_id}
            self.provider.preset_instance_properties(instance, properties)

            if not self.can_sync(instance):
                continue
            self.sync_instance(instance=instance, region_id=region_id)

    def can_sync(self, instance):
        ip = self.provider.build_asset_ip(instance, self.task.ip_network_segment_group)
        return contains_ip(ip, self.task.ip_network_segment_group)

    def sync_instance(self, instance, region_id):
        try:
            print("{}".format("-" * 50))
            instance_id = self.provider.get_instance_id(instance)
            print("实例: {}, 地域: {}".format(instance_id, region_id))
            asset, created = self.create_or_update_asset(instance=instance)
            if created:
                status = const.InstanceStatusChoices.sync
                result_key = 'new'
            else:
                status = const.InstanceStatusChoices.exist
                result_key = 'sync'
            result = {'id': instance_id, 'region': region_id, 'asset': asset.hostname}
            self.create_or_update_sync_instance(status, instance_id, region_id, asset)
        except Exception as e:
            try:
                instance_id = self.provider.get_instance_id(instance)
            except:
                instance_id = ''
            if instance_id is None:
                instance_id = ''
            colored_printer.red("同步实例失败! {} {}".format(instance_id, e))
            status = const.InstanceStatusChoices.unsync
            result_key = 'unsync'
            result = {'id': instance_id, 'region': region_id}
            self.create_or_update_sync_instance(status, instance_id, region_id, asset=None)

        self.cloud_instance_ids.append(instance_id)
        self.result[result_key].append(result)

    def create_or_update_sync_instance(self, status, instance_id, region_id, asset):
        from .models import SyncInstanceDetail
        instance = SyncInstanceDetail.objects.filter(task=self.task, instance_id=instance_id).first()
        if not instance:
            # 创建实例详情
            instance = SyncInstanceDetail.objects.create(
                task=self.task, execution=self.execution, instance_id=instance_id, region=region_id,
                asset=asset, status=status
            )
            return instance
        # 更新实例详情
        if instance.status != status:
            instance.status = status
            instance.execution = self.execution
        instance.asset = asset
        instance.save()
        return instance

    @staticmethod
    def get_asset(instance_uuid, asset_id):
        # <v2.6版本Default org_id=''，asset_id=instance_id
        # >v2.6版本Default org_id='uuid', asset_id = org_id + instance_id
        # 导致创建重复的资产
        asset = get_object_or_none(Asset, id=instance_uuid)
        if not asset:
            asset = get_object_or_none(Asset, id=asset_id)
        return asset

    def get_asset_admin_user(self, platform):
        if platform.name == 'Windows':
            admin_user = self.task.windows_admin_user
        else:
            admin_user = self.task.unix_admin_user
        return admin_user

    def create_or_update_asset(self, instance):
        asset_id = self.provider.build_asset_id(instance)
        ip = self.provider.build_asset_ip(instance, self.task.ip_network_segment_group)
        public_ip = self.provider.build_asset_public_ip(instance)
        hostname = self.provider.build_asset_hostname(instance, self.task.hostname_strategy, ip)
        instance_uuid = self.provider.get_instance_uuid(instance)
        platform = self.provider.build_asset_platform(instance)
        # 获取 资产
        asset = self.get_asset(instance_uuid, asset_id)
        # 获取 管理用户
        platform = asset.platform if asset else platform
        admin_user = self.get_asset_admin_user(platform)
        attrs = {
            'ip': ip,
            'public_ip': public_ip,
            'hostname': hostname,
            'admin_user': admin_user,
            'created_by': 'System'
        }
        # 更新资产
        if asset:
            print("资产已经存在! 资产: {}".format(asset))
            if not self.task.is_always_update:
                return asset, False
            # 更新资产信息
            print("准备更新资产! 主机名称: {}".format(hostname))
            with transaction.atomic():
                for attr, value in attrs.items():
                    setattr(asset, attr, value)
                asset.save()
            print("资产已经更新! 资产: {}".format(asset))
            return asset, False

        # 创建资产
        attrs.update({
            'id': asset_id,
            'platform': platform,
            'protocols': self.task.protocols
        })
        print("准备创建资产! 主机名称: {}".format(hostname))
        with transaction.atomic():
            asset = Asset.objects.create(**attrs)
            with translation.override('en'):
                self.set_asset_node(asset=asset, instance=instance)
                self.set_asset_domain(asset=asset, instance=instance)
        print("资产创建成功! 资产: {}".format(asset))
        return asset, True

    def set_asset_node(self, asset, instance):
        """
        :params asset: Asset instance
        :params instance: EC2 instance
        """
        # 创建节点
        nodes_name = self.provider.build_asset_nodes_name(instance=instance)
        node = self.task.node
        for node_name in nodes_name:
            node, created = node.get_or_create_child(node_name)
        # 设置节点
        print("添加资产到节点: {}".format(node.full_value))
        # 先添加目标节点，再从当前组织根节点中移除
        # 如果使用asset.nodes.set()方法进行操作，类似于先remove再add，最终资产还是会同时存在于目标节点和组织根节点中
        # 因为在资产-节点移除信号中，如果发现资产不属于任何节点会添加到组织根节点中
        asset.nodes.add(node)
        org_root = Node.org_root()
        asset.nodes.remove(org_root)

    def set_asset_domain(self, asset, instance):
        """
        :params asset: Asset instance
        :instance: EC2 instance
        """
        # 创建网域
        domain_id = self.provider.build_asset_domain_id(instance)
        domain_name = self.provider.build_asset_domain_name(instance)
        defaults = {'id': domain_id, 'name': domain_name, 'comment': domain_name}
        domain, created = Domain.objects.get_or_create(id=domain_id, defaults=defaults)
        # 添加网域
        print('添加资产到网域: {}'.format(domain))
        asset.domain = domain
        asset.save()
