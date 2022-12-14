# -*- coding: utf-8 -*-
#
from django.db.models.signals import (
    post_save, m2m_changed, pre_save, pre_delete, post_delete
)
from django.dispatch import receiver

from common.exceptions import M2MReverseNotAllowed
from common.const.signals import POST_ADD
from common.utils import get_logger
from common.decorator import on_transaction_commit
from assets.models import Asset, SystemUser, Node, AuthBook
from users.models import User
from orgs.utils import tmp_to_root_org
from assets.tasks import (
    push_system_user_to_assets_manual,
    push_system_user_to_assets,
    add_nodes_assets_to_system_users
)

logger = get_logger(__file__)


@receiver(m2m_changed, sender=SystemUser.assets.through)
@on_transaction_commit
def on_system_user_assets_change(instance, action, model, pk_set, **kwargs):
    logger.debug("System user assets change signal recv: {}".format(instance))

    if not instance:
        logger.debug('No system user found')
        return

    if model == Asset:
        system_user_ids = [instance.id]
        asset_ids = pk_set
    else:
        system_user_ids = pk_set
        asset_ids = [instance.id]

    org_id = instance.org_id

    with tmp_to_root_org():
        authbooks = AuthBook.objects.filter(
            asset_id__in=asset_ids,
            systemuser_id__in=system_user_ids
        )
        if action == POST_ADD:
            authbooks.update(org_id=org_id)

    save_action_mapper = {
        'pre_add': pre_save,
        'post_add': post_save,
        'pre_remove': pre_delete,
        'post_remove': post_delete
    }

    for ab in authbooks:
        ab.org_id = org_id

        save_action = save_action_mapper[action]
        logger.debug('Send AuthBook post save signal: {} -> {}'.format(action, ab.id))
        save_action.send(sender=AuthBook, instance=ab, created=True)

    if action == POST_ADD:
        for system_user_id in system_user_ids:
            push_system_user_to_assets.delay(system_user_id, asset_ids)


@receiver(m2m_changed, sender=SystemUser.users.through)
@on_transaction_commit
def on_system_user_users_change(sender, instance: SystemUser, action, model, pk_set, reverse, **kwargs):
    if action != POST_ADD:
        return

    if reverse:
        raise M2MReverseNotAllowed

    if not instance.username_same_with_user:
        return

    logger.debug("System user users change signal recv: {}".format(instance))
    usernames = model.objects.filter(pk__in=pk_set).values_list('username', flat=True)

    for username in usernames:
        push_system_user_to_assets_manual.delay(instance, username)


@receiver(m2m_changed, sender=SystemUser.nodes.through)
@on_transaction_commit
def on_system_user_nodes_change(sender, instance=None, action=None, model=None, pk_set=None, **kwargs):
    if action != POST_ADD:
        return
    logger.info("System user nodes update signal recv: {}".format(instance))

    queryset = model.objects.filter(pk__in=pk_set)
    if model == Node:
        nodes_keys = queryset.values_list('key', flat=True)
        system_users = [instance]
    else:
        nodes_keys = [instance.key]
        system_users = queryset
    add_nodes_assets_to_system_users.delay(nodes_keys, system_users)


@receiver(m2m_changed, sender=SystemUser.groups.through)
def on_system_user_groups_change(instance, action, pk_set, reverse, **kwargs):
    if action != POST_ADD:
        return
    if reverse:
        raise M2MReverseNotAllowed
    logger.info("System user groups update signal recv: {}".format(instance))

    users = User.objects.filter(groups__id__in=pk_set).distinct()
    instance.users.add(*users)


@receiver(post_save, sender=SystemUser, dispatch_uid="jms")
@on_transaction_commit
def on_system_user_update(instance: SystemUser, created, **kwargs):
    if instance and not created:
        logger.info("System user update signal recv: {}".format(instance))
        assets = instance.assets.all().valid()
        push_system_user_to_assets.delay(instance.id, [_asset.id for _asset in assets])
        # add assets to su_from
        instance.add_related_assets_to_su_from_if_need(assets)
