# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from common.validators import ProjectUniqueValidator
from common.mixins import BulkSerializerMixin, CommonSerializerMixin
from ..utils import get_current_org_id_for_serializer


__all__ = [
    "OrgResourceSerializerMixin", "BulkOrgResourceSerializerMixin",
    "BulkOrgResourceModelSerializer", "OrgResourceModelSerializerMixin",
]


class OrgResourceSerializerMixin(CommonSerializerMixin, serializers.Serializer):
    """
    При пакетной работе с ресурсами через API автоматически добавлять обязательный атрибут org_id к каждому ресурсу со значением current_org_id
    (В то же время подготовьтесь к serializer.is_valid() для проверки unique_together модели)
    Поскольку поле HiddenField недоступно для чтения, org_id нельзя получить, когда API получает информацию об активах.
    Но coco нужно поле org_id актива, поэтому измените его на тип CharField
    """
    org_id = serializers.ReadOnlyField(default=get_current_org_id_for_serializer, label=_("Organization"))
    org_name = serializers.ReadOnlyField(label=_("Org name"))

    def get_validators(self):
        _validators = super().get_validators()
        validators = []

        for v in _validators:
            if isinstance(v, UniqueTogetherValidator) \
                    and "org_id" in v.fields:
                v = ProjectUniqueValidator(v.queryset, v.fields)
            validators.append(v)
        return validators

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(["org_id", "org_name"])
        return fields


class OrgResourceModelSerializerMixin(OrgResourceSerializerMixin, serializers.ModelSerializer):
    pass


class BulkOrgResourceSerializerMixin(BulkSerializerMixin, OrgResourceSerializerMixin):
    pass


class BulkOrgResourceModelSerializer(BulkOrgResourceSerializerMixin, serializers.ModelSerializer):
    pass
