# -*- coding: utf-8 -*-
#

import os

from django.utils.module_loading import import_string


CURRENT_DIR = os.path.dirname(__file__)
PLUGINS_DIR = os.path.join(CURRENT_DIR, 'plugins')

app_name = 'xpack'


def check_license_validity():
    from .plugins.license.models import License
    return License.has_valid_license()


def find_enabled_plugins(only_name=True):
    plugins = []
    for i in os.listdir(PLUGINS_DIR):
        plug_dir = os.path.join(PLUGINS_DIR, i)
        meta_path = os.path.join(plug_dir, 'meta.py')
        meta_path_pyc = os.path.join(plug_dir, 'meta.pyc')
        if os.path.isdir(plug_dir) and any([
            os.path.exists(meta_path), os.path.exists(meta_path_pyc)
        ]):
            if only_name:
                plugins.append(i)
            else:
                plugins.append(Plugin(i))
    return plugins


def get_permed_plugins(user):
    if check_license_validity():
        all_plugins = find_enabled_plugins(only_name=False)
    else:
        all_plugins = [Plugin('license')]
    plugins = [p for p in all_plugins if p.can_admin_by(user)]
    return plugins


class Plugin:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    @property
    def dir(self):
        from django.conf import settings
        return os.path.join(settings.BASE_DIR, "xpack", "plugins", self.name)

    @property
    def module_path(self):
        return ".".join(["xpack", "plugins", self.name])

    @property
    def meta(self):
        meta = {}
        if os.path.isfile(os.path.join(self.dir, "meta.py")):
            meta_module = ".".join([self.module_path, "meta", "META"])
            meta = import_string(meta_module)
        return meta

    @property
    def verbose_name(self):
        if self.meta.get("verbose_name"):
            return self.meta["verbose_name"]
        return self.name

    @property
    def endpoint(self):
        return self.meta.get("endpoint", "/NotFoundPluginUrl")

    def can_admin_by(self, user):
        mark = 0
        if user.is_anonymous:
            mark = 0
        elif user.is_superuser:
            mark = 4
        elif user.is_org_admin:
            mark = 1
        if mark >= self.meta.get("permission", 4):
            return True
        else:
            return False


def get_xpack_context_processor():
    return [
        'xpack.context_processor.xpack_processor',
        'xpack.plugins.interface.context_processor.interface_processor',
        'xpack.plugins.license.context_processor.license_processor'
    ]


def get_xpack_templates_dir(base_dir):
    dirs = []
    for i in find_enabled_plugins():
        template_dir = os.path.join(base_dir, 'xpack', 'plugins', i, 'templates')
        if os.path.isdir(template_dir):
            dirs.append(template_dir)
    return dirs
