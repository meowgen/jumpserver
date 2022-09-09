import atexit
from pyVim import connect
from pyVmomi import vim

from .base import BaseProvider
from ..utils import colored_printer

# Vcenter 7 is used for interconnection


class Provider(BaseProvider):

    def __init__(self, account):
        super().__init__(account)
        self.host = self.account.attrs.get('host')
        self.port = self.account.attrs.get('port')
        self.username = self.account.attrs.get('username')
        self.password = self.account.attrs.get('password')
        self._service_instance = None
        self._virtual_machines = []

    def _is_valid(self):
        self.get_service_instance()

    @property
    def service_instance(self):
        if self._service_instance is None:
            self._service_instance = self.get_service_instance()
        return self._service_instance

    def get_service_instance(self):
        _service_instance = connect.SmartConnectNoSSL(
            host=self.host, port=int(self.port), user=self.username, pwd=self.password,
        )
        return _service_instance

    def get_regions(self):
        data_centers = self._get_datacenters()
        regions = {data_center.name: data_center.name for data_center in data_centers}
        return regions

    def get_instances_of_region(self, region_id):
        instances = []
        vms = self.get_virtual_machines()
        for vm in vms:
            datacenter = self._get_datacenter_about_vm(vm)
            if datacenter is None:
                msg = '虚拟机({}) 未获取到 DataCenter, 将同步至任务云服务商节点'.format(vm.summary.config.name)
                colored_printer.red(msg)
                instances.append(vm)
            elif datacenter.name != region_id:
                pass
            elif vm.summary.config.template:
                pass
            else:
                instances.append(vm)
        return instances

    def get_virtual_machines(self):
        if not self._virtual_machines:
            container_view = self._get_container_view(view_type=vim.VirtualMachine)
            self._virtual_machines = list(container_view.view)
        return self._virtual_machines

    @staticmethod
    def _get_datacenter_about_vm(vm):
        parent = vm
        while parent is not None and not isinstance(parent, vim.Datacenter):
            parent = parent.parent
        return parent

    def _get_datacenters(self):
        container_view = self._get_container_view(view_type=vim.Datacenter)
        data_centers = container_view.view
        return data_centers

    def _get_container_view(self, view_type):
        atexit.register(connect.Disconnect, self.service_instance)
        content = self.service_instance.RetrieveContent()
        container = content.rootFolder
        view_type = [view_type]
        recursive = True
        container_view = content.viewManager.CreateContainerView(container, view_type, recursive)
        return container_view

    def preset_instance_properties(self, *args, **kwargs):
        pass

    def get_instance_folders_name(self, instance):
        folders_name = []
        parent = instance.parent
        while parent is not None:
            folders_name.insert(0, parent.name)
            parent = parent.parent
        return folders_name

    def get_instance_id(self, instance):
        return instance.summary.config.instanceUuid

    def get_instance_name(self, instance):
        return instance.summary.config.name

    def get_instance_platform(self, instance):
        if 'windows' in instance.summary.config.guestFullName.lower():
            platform = 'windows'
        else:
            platform = 'linux'
        return platform

    def get_instance_private_ips(self, instance):
        net_list = instance.guest.net
        ips = []
        for net in net_list:
            ips.extend(net.ipAddress)
        return ips

    def get_instance_public_ip(self, instance):
        return instance.summary.guest.ipAddress

    def get_instance_region_id(self, instance):
        datacenter = self._get_datacenter_about_vm(instance)
        return datacenter.name

    def get_instance_vpc_id(self, instance):
        return instance.network[0].name
