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
        self.cloud_instance_ids = []
        self.result = {'new': [], 'sync': [], 'unsync': [], 'released': []}

    def run(self):
        print("Начинается выполнение задачи: {}\n".format(self.task))
        print("#"*50)

        self.account.check_update_validity()
        if self.account.validity:
            colored_printer.green('Учётная запись действительна.')
            try:
                self.sync()
                _reason = '-'
                _status = const.ExecutionStatusChoices.succeed
            except Exception as e:
                logger.error(e, exc_info=True)
                _status = const.ExecutionStatusChoices.failed
                _reason = str(e)
        else:
            colored_printer.red('Учётная запись недействительна.')
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
        print("Посмотреть путь к сведениям о задаче:\n")
        print("XPack -> Центр управления облаком -> Список задач -> Сведения о задаче (щелкните имя задачи) -> Просмотр списка истории синхронизации/списка экземпляров\n")
        print('\nИтоги: \n')
        msg = "Добавлено: {} Синхронизировано: {} Несинхронизировано: {} Выпущено {}\n".format(
            len(self.result['new']),
            len(self.result['sync']),
            len(self.result['unsync']),
            len(self.result['released'])
        )
        colored_printer.green(msg)
        print("Выполнение задачи заканчивается!\n")

    def sync(self):
        region_ids = self.task.regions
        print("Список регионов синхронизации: {}\n".format(region_ids))
        for region_id in region_ids:
            print("\n{}".format("="*50))
            print("Регион: {}".format(region_id))
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
            print("экземпляр: {}, регион: {}".format(instance_id, region_id))
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
            colored_printer.red("Не удалось синхронизировать экземпляр! {} {}".format(instance_id, e))
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
            instance = SyncInstanceDetail.objects.create(
                task=self.task, execution=self.execution, instance_id=instance_id, region=region_id,
                asset=asset, status=status
            )
            return instance
        if instance.status != status:
            instance.status = status
            instance.execution = self.execution
        instance.asset = asset
        instance.save()
        return instance

    @staticmethod
    def get_asset(instance_uuid, asset_id):
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
        asset = self.get_asset(instance_uuid, asset_id)
        platform = asset.platform if asset else platform
        admin_user = self.get_asset_admin_user(platform)
        attrs = {
            'ip': ip,
            'public_ip': public_ip,
            'hostname': hostname,
            'admin_user': admin_user,
            'created_by': 'System'
        }
        if asset:
            print("Ресурс уже существует! Ресурс: {}".format(asset))
            if not self.task.is_always_update:
                return asset, False
            print("Готово к обновлению ресурсов! Название хоста: {}".format(hostname))
            with transaction.atomic():
                for attr, value in attrs.items():
                    setattr(asset, attr, value)
                asset.save()
            print("Ресурсы обновлены! Ресурс: {}".format(asset))
            return asset, False

        attrs.update({
            'id': asset_id,
            'platform': platform,
            'protocols': self.task.protocols
        })
        print("Готово к созданию ресурсов! Название хоста: {}".format(hostname))
        with transaction.atomic():
            asset = Asset.objects.create(**attrs)
            with translation.override('en'):
                self.set_asset_node(asset=asset, instance=instance)
                self.set_asset_domain(asset=asset, instance=instance)
        print("Ресурсы созданы! Ресурс: {}".format(asset))
        return asset, True

    def set_asset_node(self, asset, instance):
        """
        :params asset: Asset instance
        :params instance: EC2 instance
        """
        nodes_name = self.provider.build_asset_nodes_name(instance=instance)
        node = self.task.node
        for node_name in nodes_name:
            node, created = node.get_or_create_child(node_name)
        print("Добавить ноды к ресурсам: {}".format(node.full_value))
        asset.nodes.add(node)
        org_root = Node.org_root()
        asset.nodes.remove(org_root)

    def set_asset_domain(self, asset, instance):
        """
        :params asset: Asset instance
        :instance: EC2 instance
        """
        domain_id = self.provider.build_asset_domain_id(instance)
        domain_name = self.provider.build_asset_domain_name(instance)
        defaults = {'id': domain_id, 'name': domain_name, 'comment': domain_name}
        domain, created = Domain.objects.get_or_create(id=domain_id, defaults=defaults)
        print('Добавить домен к ресурсу: {}'.format(domain))
        asset.domain = domain
        asset.save()
