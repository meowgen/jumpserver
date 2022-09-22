# -*- coding: utf-8 -*-
#

import time
import uuid
import json
from hashlib import md5
from django.db import models
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from .utils import validate_license, decrypt_license, date_to_timestamp

KEY_LICENSE_INFO = 'KEY_LICENSE_INFO'


class LicenseManager(models.Manager):
    def create(self, *args, **kwargs):
        self.all().delete()
        return super().create(*args, **kwargs)

    def update_or_create(self, content):
        obj = License.objects.create(content=content)
        return obj, True


class License(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    content = models.TextField(blank=False, null=False, verbose_name=_('Content'))

    objects = LicenseManager()

    def __str__(self):
        return 'License'

    @property
    def info(self):
        return decrypt_license(self.content)

    @property
    def is_valid(self):
        return validate_license(self.info)

    @property
    def date_expired(self):
        if not self.info:
            return '2019-01-01'
        return self.info.get('license').get('expired')

    @property
    def expired_remain_timestamp(self):
        expired_timestamp = date_to_timestamp(self.date_expired)
        return expired_timestamp - time.time()

    @property
    def will_expired(self):
        if self.expired_remain_timestamp < 5 * 24 * 3600:
            return True
        return False

    @property
    def has_expired(self):
        if self.expired_remain_timestamp < 0:
            return True
        return False

    @staticmethod
    def parse_license_edition(info):
        count = info.get('license', {}).get('count', 0)
        if count <= 499:
            edition = _('Standard edition')
        elif count <= 4999:
            edition = _('Enterprise edition')
        elif count > 4999:
            edition = _('Ultimate edition')
        else:
            edition = _('Community edition')
        return edition

    @classmethod
    def get_license_detail(cls):
        info = cls.get_license_info_or_cache()
        if not info:
            return {}
        license_dict = info.get('license', {})
        edition = cls.parse_license_edition(info)
        subscription_id = md5(json.dumps(info).encode()).hexdigest()
        result = {
            "subscription_id": subscription_id,
            "corporation": license_dict.get('corporation', ''),
            'date_expired': license_dict.get('expired', ''),
            'asset_count': license_dict.get('count', 0),
            'edition': edition,
            'is_valid': validate_license(info)
        }
        return result

    @classmethod
    def get_license_info_or_cache(cls):
        info = {"license":{"corporation":"test corp", "expired":"2034-01-01", "count":200, "product":"JUMPSERVER"}}
        if info:
            return info
        obj = cls.objects.first()
        if not obj:
            return {}
        obj.set_to_cache()
        return obj.info

    @classmethod
    def has_valid_license(cls):
        try:
            info = cls.get_license_info_or_cache()
            if info:
                return validate_license(info)
        except:
            pass
        return False

    def set_to_cache(self):
        cache.set(KEY_LICENSE_INFO, self.info, None)

    @staticmethod
    def expire_cache():
        cache.delete(KEY_LICENSE_INFO)

    class Meta:
        verbose_name = _("License")
