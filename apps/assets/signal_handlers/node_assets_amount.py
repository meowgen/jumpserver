# -*- coding: utf-8 -*-
#
from operator import add, sub
from django.db.models import Q, F
from django.dispatch import receiver
from django.db.models.signals import (
    m2m_changed
)

from orgs.utils import ensure_in_real_or_default_org, tmp_to_org
from common.const.signals import PRE_ADD, POST_REMOVE, PRE_CLEAR
from common.utils import get_logger
from assets.models import Asset, Node, compute_parent_key
from assets.locks import NodeTreeUpdateLock


logger = get_logger(__file__)


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_node_asset_change(sender, action, instance, reverse, pk_set, **kwargs):
    refused = (PRE_CLEAR,)
    if action in refused:
        raise ValueError

    mapper = {
        PRE_ADD: add,
        POST_REMOVE: sub
    }
    if action not in mapper:
        return

    operator = mapper[action]

    with tmp_to_org(instance.org):
        if reverse:
            node: Node = instance
            asset_pk_set = set(pk_set)
            NodeAssetsAmountUtils.update_node_assets_amount(node, asset_pk_set, operator)
        else:
            asset_pk = instance.id
            node_keys = set(Node.objects.filter(id__in=pk_set).values_list('key', flat=True))
            NodeAssetsAmountUtils.update_nodes_asset_amount(node_keys, asset_pk, operator)


class NodeAssetsAmountUtils:

    @classmethod
    def _remove_ancestor_keys(cls, ancestor_key, tree_set):
        while ancestor_key and ancestor_key in tree_set:
            tree_set.remove(ancestor_key)
            ancestor_key = compute_parent_key(ancestor_key)

    @classmethod
    def _is_asset_exists_in_node(cls, asset_pk, node_key):
        exists = Asset.objects.filter(
            Q(nodes__key__istartswith=f'{node_key}:') | Q(nodes__key=node_key)
        ).filter(id=asset_pk).exists()
        return exists

    @classmethod
    @ensure_in_real_or_default_org
    @NodeTreeUpdateLock()
    def update_nodes_asset_amount(cls, node_keys, asset_pk, operator):
        ancestor_keys = set()
        for key in node_keys:
            ancestor_keys.update(Node.get_node_ancestor_keys(key))
        node_keys -= ancestor_keys

        to_update_keys = []
        for key in node_keys:
            exists = cls._is_asset_exists_in_node(asset_pk, key)
            parent_key = compute_parent_key(key)

            if exists:
                cls._remove_ancestor_keys(parent_key, ancestor_keys)
                continue
            else:
                to_update_keys.append(key)
                while parent_key and parent_key in ancestor_keys:
                    exists = cls._is_asset_exists_in_node(asset_pk, parent_key)
                    if exists:
                        cls._remove_ancestor_keys(parent_key, ancestor_keys)
                        break
                    else:
                        to_update_keys.append(parent_key)
                        ancestor_keys.remove(parent_key)
                        parent_key = compute_parent_key(parent_key)

        Node.objects.filter(key__in=to_update_keys).update(
            assets_amount=operator(F('assets_amount'), 1)
        )

    @classmethod
    @ensure_in_real_or_default_org
    @NodeTreeUpdateLock()
    def update_node_assets_amount(cls, node: Node, asset_pk_set: set, operator=add):
        """
        При изменении отношения между узлом и несколькими активами обновите счетчик

        :param node: экземпляр ноды
        :param asset_pk_set: набор id ресурсов, это значение не будет изменено внутри
        :param operator: операция
        * -> Node
        # -> Asset

               * [3]
              / \
             *   * [2]
            /     \
           *       * [1]
          /       / \
         *   [a] #  # [b]

        """
        ancestor_keys = node.get_ancestor_keys(with_self=True)
        ancestors = Node.objects.filter(key__in=ancestor_keys).order_by('-key')
        to_update = []
        for ancestor in ancestors:
            asset_pk_set -= set(Asset.objects.filter(
                id__in=asset_pk_set
            ).filter(
                Q(nodes__key__istartswith=f'{ancestor.key}:') |
                Q(nodes__key=ancestor.key)
            ).distinct().values_list('id', flat=True))
            if not asset_pk_set:
                break
            ancestor.assets_amount = operator(F('assets_amount'), len(asset_pk_set))
            to_update.append(ancestor)
        Node.objects.bulk_update(to_update, fields=('assets_amount', 'parent_key'))
