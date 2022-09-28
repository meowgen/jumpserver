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
    STEP_READY: "К выполнению задачи всё готово",
    STEP_PERFORM_PREFLIGHT_CHECK: "Выполнить обнаружение состояния перед шифрованием",
    STEP_PERFORM_CHANGE_AUTH: "Выполнить шифрование",
    STEP_PERFORM_VERIFY_AUTH: "Проверка аутентификационных данных после выполнения шифрования",
    STEP_PERFORM_KEEP_AUTH: "Хранение информации аутентификации после выполнения шифрования",
    STEP_PERFORM_TASK_UPDATE: "Обновления статуса задачи после выполнения шифрования",
    STEP_FINISHED: "Задача выполнена"
}
