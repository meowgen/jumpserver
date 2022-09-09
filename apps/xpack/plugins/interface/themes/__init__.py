#!/usr/bin/env python
import os
import json

from django.conf import settings
from common.utils import get_logger

logger = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTRA_THEMES_DIR = os.path.join(settings.PROJECT_DIR, 'data', 'themes')
THEME_DIRS = [BASE_DIR, EXTRA_THEMES_DIR]
themes = []

with open(os.path.join(BASE_DIR, 'classic_green.json')) as f:
    default_theme = json.load(f)


def get_theme_files():
    files = []
    for d in THEME_DIRS:
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if not name.endswith('.json'):
                continue
            files.append(os.path.join(d, name))
    return files


def theme_is_valid(theme):
    default_attrs = default_theme.keys()
    default_colors = default_theme['colors'].keys()

    attrs_diff = set(default_attrs) - set(theme.keys())
    if attrs_diff:
        logger.error('Theme attrs not match required: %s, %s' % (attrs_diff, theme.get('name')))
        return False

    colors_diff = set(default_colors) - set(theme.get('colors').keys())
    if colors_diff:
        logger.error('Theme colors not match required: %s, %s' % (colors_diff, theme.get('name')))
        return False
    return True


def load_theme_from_file(file_path):
    with open(file_path) as ff:
        try:
            logger.debug('Load theme from file: %s', os.path.basename(file_path))
            theme = json.load(ff)
            if not theme_is_valid(theme):
                return None
        except Exception as e:
            logger.error('Load theme file error: %s, %s' % (file_path, e))
            return None
    return theme


def load_themes():
    themes.clear()
    files = get_theme_files()
    for file_path in files:
        theme = load_theme_from_file(file_path)
        if theme:
            themes.append(theme)
    return themes


load_themes()
