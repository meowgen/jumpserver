# -*- coding: utf-8 -*-
#


class DBTestConnectFailedError(Exception):

    def __str__(self):
        return 'Ошибка подключения к базе данных'
