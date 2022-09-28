import django_filters

from common.drf.filters import BaseFilterSet
from .models import SiteMessage


class SiteMsgFilter(BaseFilterSet):
    # Без фильтрации таблицы ассоциаций Django есть небольшая ошибка, которая будет повторно связывать одну и ту же таблицу
    # SELECT DISTINCT * FROM `notifications_sitemessage`
    #   INNER JOIN `notifications_sitemessageusers` ON (`notifications_sitemessage`.`id` = `notifications_sitemessageusers`.`sitemessage_id`)
    #   INNER JOIN `notifications_sitemessageusers` T4 ON (`notifications_sitemessage`.`id` = T4.`sitemessage_id`)
    # WHERE (`notifications_sitemessageusers`.`user_id` = '40c8f140dfa246d4861b80f63cf4f6e3' AND NOT T4.`has_read`)
    # ORDER BY `notifications_sitemessage`.`date_created` DESC LIMIT 15;
    has_read = django_filters.BooleanFilter(method='do_nothing')

    class Meta:
        model = SiteMessage
        fields = ('has_read',)
