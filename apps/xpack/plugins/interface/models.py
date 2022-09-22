# -*- coding: utf-8 -*-
#

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static

from jumpserver.context_processor import default_interface
from xpack.plugins.interface.themes import themes, default_theme


theme_mapper = {theme['name']: theme for theme in themes}


class Interface(models.Model):
    PATH_LOGO = 'xpack/logo/'

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    login_title = models.CharField(
        max_length=1024, null=True, blank=True,
        verbose_name=_('Title of login page')
    )
    login_image = models.ImageField(
        upload_to=PATH_LOGO, max_length=128, null=True, blank=True,
        verbose_name=_('Image of login page')
    )
    favicon = models.ImageField(
        upload_to=PATH_LOGO, max_length=128, null=True, blank=True,
        verbose_name=_('Website icon')
    )
    logo_index = models.ImageField(
        upload_to=PATH_LOGO, max_length=128,  null=True, blank=True,
        verbose_name=_('Logo of management page')
    )
    logo_logout = models.ImageField(
        upload_to=PATH_LOGO, max_length=128, null=True, blank=True,
        verbose_name=_('Logo of logout page')
    )
    theme = models.CharField(max_length=16, default='classic_green', verbose_name=_("Theme"))

    class Meta:
        verbose_name = _('Interface setting')

    @classmethod
    def update_theme_setting_default(cls, setting, interface):
        theme_name = interface.theme
        if theme_name not in theme_mapper:
            return setting

        if theme_name != default_theme['name']:
            setting.update({
                'logo_logout': static('img/logo_white.png'),
                'logo_index': static('img/logo_text_white.png'),
            })
            setting['theme_info'] = theme_mapper[theme_name]
        return setting

    @classmethod
    def get_interface_setting(cls):
        setting = {**default_interface}
        interface = cls.objects.first()
        if not interface:
            return setting
        # 覆盖一些默认值，如 使用白色 logo
        setting = cls.update_theme_setting_default(setting, interface)

        # 使用数据库中的配置，覆盖默认的
        for k in setting:
            value = getattr(interface, k, '')
            if not value:
                continue
            if hasattr(value, 'url'):
                value = value.url
            setting[k] = value
        return setting

    @classmethod
    def interface(cls):
        interface = cls.objects.first()
        return interface
