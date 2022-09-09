# -*- coding: utf-8 -*-
#

from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from common.signals import django_ready

from .plugins.license.models import License


@receiver(post_save, sender=License)
def on_license_update_or_create(sender, instance, created=False, **kwargs):
    instance.set_to_cache()


@receiver(post_delete, sender=License)
def on_license_delete(sender, instance=None, **kwargs):
    instance.expire_cache()


@receiver(django_ready)
def on_django_start_expire_license_cache(sender, **kwargs):
    License.expire_cache()
