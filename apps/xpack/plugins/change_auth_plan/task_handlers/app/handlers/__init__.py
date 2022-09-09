from .mysql import MySQLChangePasswordHandler
from .oracle import OracleChangePasswordHandler
from .postgre import PostgreChangePasswordHandler
from .sqlserver import SQLServerChangePasswordHandler

handler_mapper = {
    'mysql': MySQLChangePasswordHandler,
    'mariadb': MySQLChangePasswordHandler,
    'oracle': OracleChangePasswordHandler,
    'postgresql': PostgreChangePasswordHandler,
    'sqlserver': SQLServerChangePasswordHandler,
}
