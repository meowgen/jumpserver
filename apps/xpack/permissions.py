# -*- coding: utf-8 -*-
#

from rest_framework import permissions

from rbac.permissions import RBACPermission
from .utils import check_license_validity


class LicenseIsValid(permissions.BasePermission):
    def has_permission(self, request, view):
        if not check_license_validity():
            return False
        return True


RBACLicensePermission = RBACPermission & LicenseIsValid
