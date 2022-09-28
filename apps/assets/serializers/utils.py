from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


def validate_password_for_ansible(password):
    if '{{' in password:
        raise serializers.ValidationError(_('Password can not contains `{{` '))
    if "'" in password:
        raise serializers.ValidationError(_("Password can not contains `'` "))
    if '"' in password:
        raise serializers.ValidationError(_('Password can not contains `"` '))

