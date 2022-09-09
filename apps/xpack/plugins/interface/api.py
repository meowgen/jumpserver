# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets

from xpack.permissions import RBACLicensePermission
from .themes import themes
from .serializers import InterfaceSerializer
from .models import Interface


class InterfaceViewSet(viewsets.ModelViewSet):
    queryset = Interface.objects.all()
    permission_classes = (RBACLicensePermission,)
    serializer_class = InterfaceSerializer
    rbac_perms = {
        'GET': 'settings.change_interface',
        'PUT': 'settings.change_interface',
        'themes': 'settings.change_interface',
        'restore': 'settings.change_interface',
    }

    def get_object(self):
        obj = Interface.get_interface_setting()
        return obj

    def list(self, request, *args, **kwargs):
        return Response(self.get_object())

    def retrieve(self, request, *args, **kwargs):
        return Response(self.get_object())

    def put(self, request, *args, **kwargs):
        obj = Interface.interface()
        serializer = InterfaceSerializer(instance=obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            result = self.get_object()
            return Response(result)
        else:
            return Response(serializer.errors, status=400)

    @action(detail=False, methods=['GET'])
    def themes(self, request):
        return Response(themes)

    @action(detail=False, methods=['PUT'])
    def restore(self, request):
        Interface.objects.all().delete()
        return Response({"success": _("Restore default successfully.")})
