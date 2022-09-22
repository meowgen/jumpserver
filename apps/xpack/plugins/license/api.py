# -*- coding: utf-8 -*-

import chardet
import codecs
from rest_framework import generics
from rest_framework.response import Response
from common.utils import get_logger
from django.utils.translation import gettext as _
from settings.models import Setting
from .utils import validate_license, decrypt_license
from .serializers import LicenseDetailSerializer, LicenseImportSerializer
from .models import License
from orgs.utils import tmp_to_root_org
from assets.models import Asset

logger = get_logger(__file__)


class LicenseDetailApi(generics.RetrieveAPIView):
    perm_model = Setting
    serializer_class = LicenseDetailSerializer
    rbac_perms = {
        'retrieve': 'settings.change_license'
    }

    def get_object(self):
        detail = License.get_license_detail()
        with tmp_to_root_org():
            current_asset_count = Asset.objects.count()
        detail.update({
            'current_asset_count': current_asset_count
        })
        return detail


class LicenseImportAPi(generics.CreateAPIView):
    perm_model = Setting
    serializer_class = LicenseImportSerializer
    rbac_perms = {
        'POST': 'settings.change_license'
    }

    def post(self, request, *args, **kwargs):
        serializer = LicenseImportSerializer(data=request.data)
        if serializer.is_valid():
            upload_file = serializer.validated_data['file']
            content = self.get_license_content(upload_file)
            if validate_license(decrypt_license(content)):
                License.objects.update_or_create(content=content)
                return Response(data={'status': True, 'msg': _('License import successfully')})
            return Response(data={'status': False, 'msg': _('License is invalid')})
        return Response(serializer.errors, status=400)

    @staticmethod
    def get_license_content(f):
        try:
            det_result = chardet.detect(f.read())
            f.seek(0)
            content = f.read().decode(det_result['encoding']).strip(
                codecs.BOM_UTF8.decode()
            )
        except Exception as e:
            logger.debug('License get file content error: {}'.format(e))
            return b''
        else:
            return content
