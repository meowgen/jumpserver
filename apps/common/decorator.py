# -*- coding: utf-8 -*-
#
from django.db import transaction


def on_transaction_commit(func):
    """
    Если on_commit не вызывается, добавление значения поля «многие ко многим» завершается ошибкой при создании объекта.    """
    def inner(*args, **kwargs):
        transaction.on_commit(lambda: func(*args, **kwargs))
    return inner


class Singleton(object):
    """ Одиночка """
    def __init__(self, cls):
        self._cls = cls
        self._instance = {}

    def __call__(self):
        if self._cls not in self._instance:
            self._instance[self._cls] = self._cls()
        return self._instance[self._cls]
