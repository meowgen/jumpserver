from __future__ import absolute_import

from django.urls import path

from .. import api

urlpatterns = [
    path('detail', api.LicenseDetailApi.as_view(), name='license-Detail'),
    path('import', api.LicenseImportAPi.as_view(), name='license-Import'),
]
