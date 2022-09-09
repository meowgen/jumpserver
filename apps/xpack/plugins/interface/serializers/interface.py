from rest_framework import serializers
from django.utils.translation import get_language

from xpack.plugins.interface.themes import themes
from ..models import Interface


def get_themes_choices():
    themes_choices = []
    lang = get_language() or 'zh'
    lang = lang[:2]

    for theme in themes:
        display = theme['display']
        if isinstance(display, dict):
            display = display.get(lang) or list(display.values())[0]
        themes_choices.append((theme.get('name'), display))
    themes_choices.sort(key=lambda x: x[1])
    return themes_choices


class InterfaceSerializer(serializers.ModelSerializer):
    theme = serializers.ChoiceField(choices=get_themes_choices(), default='default')

    class Meta:
        model = Interface
        fields = [
            'login_title', 'login_image', 'favicon',
            'logo_index', 'logo_logout', 'theme',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        theme = self.fields.get('theme')
        if not theme:
            return
        theme.choices = get_themes_choices()

    def save(self, **kwargs):
        instance = Interface.objects.first()
        validated_data = {**self.validated_data, **kwargs}

        if not instance:
            instance = Interface()

        for k, v in validated_data.items():
            if v:
                setattr(instance, k, v)
        instance.save()
        return instance

