# -*- coding: utf-8 -*-

from rest_framework import serializers


class LicenseDetailSerializer(serializers.Serializer):
    subscription_id = serializers.CharField(max_length=128, default='')
    corporation = serializers.CharField(max_length=128, default='')
    date_expired = serializers.CharField(max_length=128, default='')
    asset_count = serializers.IntegerField(default=0)
    current_asset_count = serializers.IntegerField(default=0)
    edition = serializers.CharField(default='')
    is_valid = serializers.BooleanField(read_only=True)


class LicenseImportSerializer(serializers.Serializer):
    file = serializers.FileField()
