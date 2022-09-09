# -*- coding: utf-8 -*-
#

import os
from django.urls import path, include

from ..utils import find_enabled_plugins, PLUGINS_DIR


app_name = 'xpack'


def auto_find_url():
    paths = []
    plugins = find_enabled_plugins()
    for i in plugins:
        url_path = os.path.join(PLUGINS_DIR, i, 'urls', 'api_urls.py')
        url_path_pyc = os.path.join(PLUGINS_DIR, i, 'urls', 'api_urls.pyc')

        if not any([os.path.isfile(url_path), os.path.isfile(url_path_pyc)]):
            continue
        url_file_path = ".".join(['xpack.plugins', i, 'urls', 'api_urls'])
        paths.append(path(i.replace('_', '-') + '/', include((url_file_path, 'xpack'), namespace=i)))
    return paths


urlpatterns = auto_find_url()