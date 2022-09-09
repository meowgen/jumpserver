# -*- coding: utf-8 -*-
#

string_punctuation = '!#$%&()*+,-.:;<=>?@[]^_~'
DEFAULT_PASSWORD_LENGTH = 30
DEFAULT_PASSWORD_RULES = {
    'length': DEFAULT_PASSWORD_LENGTH,
    'symbol_set': string_punctuation
}

STEP_READY = 0
STEP_PERFORM_PREFLIGHT_CHECK = 1
STEP_PERFORM_CHANGE_AUTH = 2
STEP_PERFORM_VERIFY_AUTH = 3
STEP_PERFORM_KEEP_AUTH = 4
STEP_PERFORM_TASK_UPDATE = 5
STEP_FINISHED = 10

STEP_DESCRIBE_MAP = {
    STEP_READY: "任务准备就绪",
    STEP_PERFORM_PREFLIGHT_CHECK: "执行改密前的条件检测",
    STEP_PERFORM_CHANGE_AUTH: "执行改密",
    STEP_PERFORM_VERIFY_AUTH: "执行改密后对认证信息的校验",
    STEP_PERFORM_KEEP_AUTH: "执行改密后对认证信息的保存",
    STEP_PERFORM_TASK_UPDATE: "执行改密后对任务状态的更新",
    STEP_FINISHED: "执行任务完成"
}
