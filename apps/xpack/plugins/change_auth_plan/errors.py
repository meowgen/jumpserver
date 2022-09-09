# -*- coding: utf-8 -*-
#


class DBTestConnectFailedError(Exception):

    def __str__(self):
        return '数据库连接失败'
