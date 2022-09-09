from .asset.manager import AssetExecutionManager
from .asset.handlers import AssetChangePasswordHandler
from .app.manager import AppExecutionManager
from .app.handlers import (
    MySQLChangePasswordHandler,
    OracleChangePasswordHandler,
    PostgreChangePasswordHandler,
    SQLServerChangePasswordHandler,
)


class ExecutionManager:
    """
    根据改密资产/应用类型选择不同处理类
    """
    manager_type = {
        'asset': AssetExecutionManager,
        'app': AppExecutionManager,
    }

    def __new__(cls, execution):
        manager = cls.manager_type[execution.manager_name]
        return manager(execution)


class TaskHandler:
    handler_type = {
        'asset': AssetChangePasswordHandler,
        'mysql': MySQLChangePasswordHandler,
        'mariadb': MySQLChangePasswordHandler,
        'oracle': OracleChangePasswordHandler,
        'postgresql': PostgreChangePasswordHandler,
        'sqlserver': SQLServerChangePasswordHandler,
    }

    def __new__(cls, task, show_step_info):
        handler = cls.handler_type[task.handler_name]
        return handler(task, show_step_info)
